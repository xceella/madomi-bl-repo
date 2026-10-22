package eu.kanade.tachiyomi.extension.pt.portalyaoi

import android.util.Base64
import eu.kanade.tachiyomi.multisrc.madara.MadaraNoAjax
import eu.kanade.tachiyomi.source.model.FilterList
import eu.kanade.tachiyomi.source.model.MangasPage
import eu.kanade.tachiyomi.source.model.SManga
import keiyoushi.annotation.Source
import keiyoushi.network.get
import keiyoushi.network.rateLimit
import keiyoushi.utils.parseAs
import keiyoushi.utils.runWebView
import kotlinx.coroutines.CancellationException
import okhttp3.HttpUrl.Companion.toHttpUrl
import okhttp3.OkHttpClient
import org.jsoup.Jsoup
import org.jsoup.nodes.Document
import org.jsoup.nodes.Element
import java.io.IOException
import java.time.format.DateTimeFormatter
import java.util.Locale
import kotlin.time.Duration.Companion.seconds

/**
 * XBL Portal Yaoi: keep upstream Madara reader and add a resilient search
 * for the site's newer /portal-yaoi/ catalogue and /manga/ title URLs.
 * Fail explicitly for HTTP 403 instead of presenting a misleading empty list.
 */
@Source
abstract class PortalYaoi : MadaraNoAjax() {

    override val chapterDateFormat = DateTimeFormatter.ofPattern("dd/MM/yyyy", Locale("pt", "BR"))

    override fun OkHttpClient.Builder.configureClient() = rateLimit(1, 2.seconds) {
        !it.encodedPath.startsWith("/wp-content/uploads/")
    }

    override suspend fun getPopularManga(page: Int): MangasPage {
        val url = "$baseUrl/portal-yaoi/".toHttpUrl().newBuilder()
            .addQueryParameter("page", page.toString())
            .build().toString()
        val document = getCatalogueDocument(url)
        val mangas = extractWorks(document, "")
        val hasNext = document.select("a[href*='page=${page + 1}'], a[href*='/page/${page + 1}/']").isNotEmpty()
        return MangasPage(mangas, hasNext)
    }

    override suspend fun getSearchMangaList(page: Int, query: String, filters: FilterList): MangasPage {
        if (query.isBlank()) return getPopularManga(page)
        if (page > 1) return MangasPage(emptyList(), false)

        // Different versions of the Portal have used both WordPress search
        // and a dedicated catalogue. Test both with site-relative requests.
        val targets = listOf(
            "$baseUrl/".toHttpUrl().newBuilder()
                .addQueryParameter("s", query)
                .addQueryParameter("post_type", "wp-manga")
                .build().toString(),
            "$baseUrl/portal-yaoi/".toHttpUrl().newBuilder()
                .addQueryParameter("s", query)
                .build().toString(),
        )

        var forbidden = false
        for (target in targets) {
            val response = try {
                client.get(target, ensureSuccess = false)
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                continue
            }
            val code = response.code
            val html = response.body.string()
            if (code == 403) {
                forbidden = true
                continue
            }
            if (code !in 200..299) continue

            val mangas = extractWorks(Jsoup.parse(html, target), query)
            if (mangas.isNotEmpty()) return MangasPage(mangas, false)
        }

        // Browser rendering is only a fallback; keep the normal HTTP path fast.
        // Unlike silently returning an empty result, an access challenge should
        // be visible in the error message when the request was blocked.
        val rendered = try {
            runWebView<String>(12.seconds) {
                userAgent = headers["User-Agent"].orEmpty()
                blockImages = true
                onPageFinished {
                    evaluateJs("document.documentElement.outerHTML") { resolve(it.parseAs<String>()) }
                }
                loadUrl(targets.last())
            }
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            null
        }

        if (rendered != null) {
            val mangas = extractWorks(Jsoup.parse(rendered, targets.last()), query)
            if (mangas.isNotEmpty()) return MangasPage(mangas, false)
            if (rendered.contains("cloudflare", ignoreCase = true) ||
                rendered.contains("you have been blocked", ignoreCase = true)
            ) {
                forbidden = true
            }
        }

        if (forbidden) {
            throw IOException("Portal Yaoi: acesso HTTP 403/bloqueio na busca. Abra a fonte na WebView e verifique o acesso ao site.")
        }
        return MangasPage(emptyList(), false)
    }

    private suspend fun getCatalogueDocument(url: String): Document {
        val response = client.get(url, ensureSuccess = false)
        if (response.code == 403) {
            throw IOException("Portal Yaoi: HTTP 403 no catálogo. Abra a WebView para verificar o bloqueio.")
        }
        if (!response.isSuccessful) {
            throw IOException("Portal Yaoi: HTTP ${response.code} no catálogo.")
        }
        return Jsoup.parse(response.body.string(), url)
    }

    private fun extractWorks(document: Document, query: String): List<SManga> {
        val normalized = query.trim().lowercase()
        return document.select("a[href*='/manga/']")
            .mapNotNull { element ->
                val href = element.attr("abs:href").ifBlank { element.attr("href") }
                if (!href.startsWith("http")) return@mapNotNull null
                val remainder = href.substringAfter("/manga/", "")
                val slug = remainder.substringBefore('/').substringBefore('?').trim()
                // Only /manga/{slug}/ links: exclude chapter/deep links.
                if (slug.isBlank()) return@mapNotNull null
                val extra = remainder.substringAfter('/', "")
                if (extra.isNotBlank() && !extra.startsWith("?") && !extra.startsWith("#")) return@mapNotNull null

                val img = element.selectFirst("img") ?: element.parent()?.selectFirst("img")
                val heading = element.selectFirst("h2, h3, h4, .title, .manga-title")
                    ?: element.parent()?.selectFirst("h2, h3, h4, .title, .manga-title")
                val fallbackName = slug.replace('-', ' ')
                val title = heading?.text()?.trim()?.takeIf { it.isNotBlank() }
                    ?: img?.attr("alt")?.trim()?.takeIf { it.isNotBlank() }
                    ?: element.attr("title").trim().takeIf { it.isNotBlank() }
                    ?: fallbackName

                if (normalized.isNotBlank() &&
                    !title.lowercase().contains(normalized) &&
                    !fallbackName.lowercase().contains(normalized)
                ) {
                    return@mapNotNull null
                }

                SManga.create().apply {
                    setUrlWithoutDomain(href)
                    this.title = title
                    thumbnail_url = img?.let { image ->
                        image.attr("abs:data-src").ifBlank { image.attr("abs:src") }
                    }?.takeIf { it.startsWith("http") }
                }
            }
            .distinctBy { it.url }
    }

    override fun imageFromElement(element: Element): String? = when {
        element.hasAttr("data-obf") -> decodePageUrl(element.attr("data-obf"))
        else -> super.imageFromElement(element)
    }

    private fun decodePageUrl(value: String): String = String(Base64.decode(value.reversed(), Base64.DEFAULT))
}
