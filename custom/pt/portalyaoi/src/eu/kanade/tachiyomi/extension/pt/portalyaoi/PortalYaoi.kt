package eu.kanade.tachiyomi.extension.pt.portalyaoi

import android.util.Base64
import eu.kanade.tachiyomi.multisrc.madara.MadaraNoAjax
import eu.kanade.tachiyomi.source.model.FilterList
import eu.kanade.tachiyomi.source.model.MangasPage
import eu.kanade.tachiyomi.source.model.Page
import eu.kanade.tachiyomi.source.model.SChapter
import eu.kanade.tachiyomi.source.model.SManga
import eu.kanade.tachiyomi.source.model.SMangaUpdate
import keiyoushi.annotation.Source
import keiyoushi.network.get
import keiyoushi.network.rateLimit
import keiyoushi.utils.parseAs
import keiyoushi.utils.runWebView
import kotlinx.coroutines.CancellationException
import okhttp3.HttpUrl.Companion.toHttpUrl
import okhttp3.OkHttpClient
import okhttp3.Request
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

    override suspend fun fetchMangaUpdate(
        manga: SManga,
        chapters: List<SChapter>,
        fetchDetails: Boolean,
        fetchChapters: Boolean,
    ): SMangaUpdate {
        val url = getMangaUrl(manga)
        val response = client.get(url, ensureSuccess = false)
        if (!response.isSuccessful) {
            throw IOException("Portal Yaoi: HTTP ${response.code} nos detalhes da obra.")
        }
        val document = Jsoup.parse(response.body.string(), url)

        // The 2026 site uses .manga-hero-* rather than the old Madara summary.
        // Never call the old Madara detail parser: missing elements cause NPE.
        val updatedManga = if (fetchDetails) {
            manga.apply {
                title = document.selectFirst(".manga-hero-title, h1")
                    ?.text()?.trim()?.takeIf { it.isNotBlank() } ?: title

                thumbnail_url = document.selectFirst("meta[property=og:image]")
                    ?.attr("content")?.takeIf { it.startsWith("http") } ?: thumbnail_url

                description = document.selectFirst(".synopsis-scrollable-content .summary__content")
                    ?.text()?.trim()?.takeIf { it.isNotBlank() }
                    ?: document.selectFirst(".synopsis-scrollable-content")
                        ?.text()?.trim()?.takeIf { it.isNotBlank() }
                    ?: description

                author = document.select(".manga-hero-author .author-name a").text()
                    .trim().takeIf { it.isNotBlank() } ?: author
                artist = document.select(".brand-badge.badge-artist a").text()
                    .trim().takeIf { it.isNotBlank() } ?: artist
                genre = document.select(".manga-hero-genres a")
                    .eachText().filter { it.isNotBlank() }.distinct()
                    .joinToString(", ").takeIf { it.isNotBlank() } ?: genre

                val siteStatus = document.selectFirst(".brand-badge.badge-status")
                    ?.text()?.trim()?.lowercase().orEmpty()
                status = when {
                    siteStatus.contains("completo") || siteStatus.contains("conclu") -> SManga.COMPLETED
                    siteStatus.contains("lançamento") || siteStatus.contains("andamento") -> SManga.ONGOING
                    else -> status
                }
            }
        } else {
            manga
        }

        val updatedChapters = if (fetchChapters) {
            document.select(".manga-chapters-list a.chapter-link, .listing-chapters_wrap a.chapter-link")
                .mapNotNull { element ->
                    val href = element.attr("abs:href").ifBlank { element.attr("href") }
                    if (!href.startsWith("http")) return@mapNotNull null
                    val name = element.text().trim()
                    if (name.isBlank()) return@mapNotNull null

                    SChapter.create().apply {
                        setUrlWithoutDomain(href)
                        this.name = name
                    }
                }
                .distinctBy { it.url }
                .also { if (it.isEmpty()) throw IOException("Portal Yaoi: nenhuma entrada .chapter-link encontrada na obra.") }
        } else {
            chapters
        }
        return SMangaUpdate(updatedManga, updatedChapters)
    }

    override fun getChapterUrl(chapter: SChapter): String {
        val path = chapter.url
        return when {
            path.startsWith("https://") || path.startsWith("http://") -> path
            path.startsWith("/manga/") -> "$baseUrl$path"
            else -> super.getChapterUrl(chapter)
        }
    }

    override suspend fun getPageList(chapter: SChapter): List<Page> {
        val chapterUrl = getChapterUrl(chapter)
        val response = client.get(chapterUrl, ensureSuccess = false)
        if (!response.isSuccessful) {
            throw IOException("Portal Yaoi: HTTP ${response.code} ao abrir o capítulo.")
        }

        val html = response.body.string()
        val document = Jsoup.parse(html, chapterUrl)
        // The reader mixes actual image URLs and transparent GIF placeholders.
        // Encoded nodes use base64(reverse(XOR(url, runtimeKey))).
        val runtimeKey = Regex("""(?:var|let|const)\s+_k\s*=\s*["']([^"']+)["']""")
            .find(html)?.groupValues?.getOrNull(1).orEmpty()

        val urls = document.select(".reading-content img.wp-manga-chapter-img")
            .mapNotNull { image ->
                val obfuscated = image.attr("data-content-node")
                val url = when {
                    obfuscated.isNotBlank() && runtimeKey.isNotBlank() ->
                        decodeContentNode(obfuscated, runtimeKey)
                    image.hasAttr("data-obf") ->
                        decodePageUrl(image.attr("data-obf"))
                    else -> {
                        listOf("data-src", "data-lazy-src", "src")
                            .asSequence()
                            .map { image.attr("abs:$it") }
                            .firstOrNull { it.startsWith("http://") || it.startsWith("https://") }
                    }
                }
                url?.takeIf { it.startsWith("http://") || it.startsWith("https://") }
            }
            .distinct()

        if (urls.isEmpty()) {
            throw IOException("Portal Yaoi: nenhuma imagem válida encontrada no leitor (HTML ${html.length}, chave=${runtimeKey.isNotEmpty()}).")
        }
        return urls.mapIndexed { index, url -> Page(index, chapterUrl, url) }
    }

    private fun decodeContentNode(value: String, key: String): String? {
        if (key.isEmpty()) return null
        return try {
            val bytes = Base64.decode(value.reversed(), Base64.DEFAULT)
            val decoded = CharArray(bytes.size) { index ->
                ((bytes[index].toInt() and 0xff) xor key[index % key.length].code).toChar()
            }
            String(decoded).takeIf { it.startsWith("http://") || it.startsWith("https://") }
        } catch (e: IllegalArgumentException) {
            null
        }
    }

    override fun imageRequest(page: Page): Request = super.imageRequest(page).newBuilder()
        .header("Referer", page.url.ifBlank { "$baseUrl/" })
        .build()

    override fun imageFromElement(element: Element): String? = when {
        element.hasAttr("data-obf") -> decodePageUrl(element.attr("data-obf"))
        else -> super.imageFromElement(element)
    }

    private fun decodePageUrl(value: String): String = String(Base64.decode(value.reversed(), Base64.DEFAULT))
}
