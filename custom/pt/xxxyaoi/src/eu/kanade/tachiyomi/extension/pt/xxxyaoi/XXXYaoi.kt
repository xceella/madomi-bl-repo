package eu.kanade.tachiyomi.extension.pt.xxxyaoi

import android.webkit.WebResourceResponse
import eu.kanade.tachiyomi.multisrc.madara.MadaraNoAjax
import eu.kanade.tachiyomi.source.model.FilterList
import eu.kanade.tachiyomi.source.model.MangasPage
import eu.kanade.tachiyomi.source.model.Page
import eu.kanade.tachiyomi.source.model.SChapter
import keiyoushi.annotation.Source
import keiyoushi.network.Fetch
import keiyoushi.network.get
import keiyoushi.network.post
import keiyoushi.network.rateLimit
import keiyoushi.utils.asJsoup
import keiyoushi.utils.parseAs
import keiyoushi.utils.runWebView
import kotlinx.coroutines.CancellationException
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.booleanOrNull
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.intOrNull
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import okhttp3.FormBody
import okhttp3.Headers
import okhttp3.OkHttpClient
import org.jsoup.Jsoup
import org.jsoup.nodes.Document
import org.jsoup.nodes.Element
import java.io.ByteArrayInputStream
import java.io.IOException
import java.time.format.DateTimeFormatter
import kotlin.time.Duration.Companion.seconds

/**
 * XBL PT-BR fork of Keiyoushi XXXYaoi.
 *
 * The website changed the markup for its chapter labels. Some chapter pages
 * also render image markup with JavaScript, so a plain HTML request can contain
 * zero reader images even when those images appear in a normal browser.
 */
@Source
abstract class XXXYaoi : MadaraNoAjax() {

    override val chapterDateFormat = DateTimeFormatter.ofPattern("dd/MM/yyyy")

    override fun OkHttpClient.Builder.configureClient() = rateLimit(3, 1.seconds)

    override fun Headers.Builder.configureHeaders() = set("Upgrade-Insecure-Requests", "1")
        .set("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")
        .set("Sec-GPC", "1")
        .set("Sec-Fetch-User", "?1")
        .set("Sec-Fetch-Site", "none")
        .set("Sec-Fetch-Mode", "navigate")
        .set("Sec-Fetch-Dest", "document")
        .set("Priority", "u=0, i")
        .set("Pragma", "no-cache")

    // XXX Yaoi now lists its catalog under /biblioteca/, while series URLs stay under /bl/.
    override val mangaSubString = "biblioteca"

    // New catalog cards have no Madara post IDs. Keep stable path-based IDs.
    override val supportsPostId = false

    override val mangaDetailsSelectorTitle = ".xyaoi-main-title, h1"
    override val mangaDetailsSelectorAuthor = "a[href*=author]"
    override val mangaDetailsSelectorArtist = "a[href*=artist]"
    override val mangaDetailsSelectorStatus = "span:contains(status) + span"
    override val mangaDetailsSelectorDescription = "[class*=synopsis]"

    // Both the library and search now render .xyaoi-card (not .xyaoi-search-card).
    override fun archiveSelector() = ".xyaoi-card"
    override fun searchCardSelector() = archiveSelector()

    override val archiveUrlSelector = ".xyaoi-card-title a"

    // Since November 2026 the site's WordPress ?s=... search route returns HTTP 404.
    // The public /biblioteca/ search uses this WordPress AJAX action instead.
    override suspend fun getSearchMangaList(page: Int, query: String, filters: FilterList): MangasPage {
        if (query.isBlank()) return super.getSearchMangaList(page, query, filters)

        val requestBody = FormBody.Builder()
            .add("action", "xyaoi_library_filter")
            .add("search", query.trim())
            .add("status", "")
            .add("genre", "")
            .add("orderby", "latest")
            .add("page", page.toString())
            .build()

        val requestHeaders = xhrHeaders.newBuilder()
            .set("Referer", "$baseUrl/biblioteca/")
            .set("Origin", baseUrl)
            .set("Accept", "application/json, text/javascript, */*; q=0.01")
            .set("Sec-Fetch-Site", "same-origin")
            .set("Sec-Fetch-Mode", "cors")
            .set("Sec-Fetch-Dest", "empty")
            .build()

        val response = client.post(
            "$baseUrl/wp-admin/admin-ajax.php",
            requestHeaders,
            Fetch.XHR,
            requestBody,
        ).body.string().parseAs<JsonObject>()

        if (response["success"]?.jsonPrimitive?.booleanOrNull != true) {
            throw IOException("XXX Yaoi: o servidor não retornou resultados válidos da biblioteca.")
        }

        val payload = response["data"]?.jsonObject
            ?: throw IOException("XXX Yaoi: resposta sem dados da biblioteca.")
        val cardsHtml = payload["html"]?.jsonPrimitive?.contentOrNull
            ?: throw IOException("XXX Yaoi: resposta sem HTML de resultados.")
        val lastPage = payload["total_pages"]?.jsonPrimitive?.intOrNull ?: page
        val document = Jsoup.parse(cardsHtml, "$baseUrl/biblioteca/")
        return MangasPage(parseArchive(document), page < lastPage)
    }

    override fun chapterFromElement(element: Element, mangaPath: String) = super.chapterFromElement(element, mangaPath)?.apply {
        // Keep the chapter-list fix; generated c_XXXXXXXX classes are unstable.
        name = element.selectFirst(
            ".xyaoi-chapter-left > div:not(.xyaoi-chapter-thumb-wrapper) > div:first-child > span:first-child",
        )?.text()?.trim()?.takeIf(String::isNotBlank) ?: name

        val dateText = element.selectFirst(
            ".xyaoi-chapter-left > div:not(.xyaoi-chapter-thumb-wrapper) > div:last-child > span:last-child",
        )?.text()?.trim()?.takeIf(String::isNotBlank)
        if (dateText != null) {
            date_upload = parseChapterDate(dateText)
        }
    }

    override suspend fun getPageList(chapter: SChapter): List<Page> {
        val chapterUrl = getChapterUrl(chapter)
        val html = client.get(chapterUrl, Fetch.DOCUMENT).body.string()
        val direct = html.asJsoup(chapterUrl)
        val directPages = extractPages(direct, chapterUrl)
        if (directPages.isNotEmpty()) return directPages

        // Restore the JavaScript rendering used by the upstream extension.
        // Only use WebView if the static HTTP response contains no page images.
        val rendered = try {
            runWebView<String> {
                userAgent = headers["User-Agent"].orEmpty()
                interceptRequest { request ->
                    if (request.isForMainFrame) {
                        null
                    } else {
                        WebResourceResponse("text/javascript", null, 200, "OK", null, ByteArrayInputStream(ByteArray(0)))
                    }
                }
                onPageFinished {
                    evaluateJs("document.documentElement.outerHTML") { resolve(it.parseAs<String>()) }
                }
                loadData(chapterUrl, html)
            }
        } catch (e: CancellationException) {
            throw e
        } catch (e: Throwable) {
            throw IOException("XXX Yaoi: falha ao renderizar o capítulo no WebView: ${e.message}", e)
        }

        val pages = extractPages(rendered.asJsoup(chapterUrl), chapterUrl)
        if (pages.isEmpty()) {
            throw IOException("XXX Yaoi: nenhuma imagem detectada no HTML do capítulo, nem após renderização. Verifique o acesso ao site na WebView.")
        }
        return pages
    }

    private fun extractPages(document: Document, chapterUrl: String): List<Page> = document
        .select(".reading-content .page-break img, .reading-content img.wp-manga-chapter-img")
        .mapNotNull { element ->
            val imageUrl = element.attr("abs:data-src")
                .ifBlank { element.attr("abs:data-lazy-src") }
                .ifBlank { element.attr("abs:src") }
            imageUrl.takeIf { it.startsWith("http://") || it.startsWith("https://") }
        }
        .distinct()
        .mapIndexed { index, url -> Page(index, chapterUrl, url) }
}
