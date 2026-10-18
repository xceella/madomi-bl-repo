package eu.kanade.tachiyomi.extension.pt.xxxyaoi

import eu.kanade.tachiyomi.multisrc.madara.MadaraNoAjax
import keiyoushi.annotation.Source
import keiyoushi.network.get
import keiyoushi.network.rateLimit
import keiyoushi.utils.asJsoup
import okhttp3.Headers
import okhttp3.OkHttpClient
import org.jsoup.nodes.Document
import org.jsoup.nodes.Element
import java.time.format.DateTimeFormatter
import kotlin.time.Duration.Companion.seconds

/**
 * XBL PT-BR fork of Keiyoushi XXXYaoi.
 *
 * The website switched to .xyaoi-chapter-row and nested chapter labels.
 * The upstream legacy "div > span:nth-child(1)" lookup returned null and
 * its !! dereference crashed the whole chapter list on Mihon.
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

    override val mangaSubString = "bl"

    override val mangaDetailsSelectorTitle = ".xyaoi-main-title, h1"
    override val mangaDetailsSelectorAuthor = "a[href*=author]"
    override val mangaDetailsSelectorArtist = "a[href*=artist]"
    override val mangaDetailsSelectorStatus = "span:contains(status) + span"
    override val mangaDetailsSelectorDescription = "[class*=synopsis]"

    override fun searchCardSelector() = ".xyaoi-search-card"

    override val archiveUrlSelector = "h3 > a"

    override fun chapterFromElement(element: Element, mangaPath: String) = super.chapterFromElement(element, mangaPath)?.apply {
        // Use stable site container classes, not the generated c_XXXXXXXX names.
        // Never force a nullable selector: a single failed chapter must not crash all details.
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

    override suspend fun fetchChapterDocument(chapterUrl: String): Document {
        // The current site renders page-break / img elements in the initial HTML.
        // The old WebView round trip was unnecessary and could stall or time out.
        return client.get(chapterUrl).asJsoup()
    }
}
