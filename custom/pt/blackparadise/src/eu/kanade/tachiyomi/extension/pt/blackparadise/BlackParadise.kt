package eu.kanade.tachiyomi.extension.pt.blackparadise

import eu.kanade.tachiyomi.multisrc.madara.MadaraNoAjax
import eu.kanade.tachiyomi.source.model.FilterList
import eu.kanade.tachiyomi.source.model.MangasPage
import eu.kanade.tachiyomi.source.model.Page
import eu.kanade.tachiyomi.source.model.SChapter
import eu.kanade.tachiyomi.source.model.SManga
import eu.kanade.tachiyomi.source.model.SMangaUpdate
import keiyoushi.annotation.Source
import keiyoushi.network.Fetch
import keiyoushi.network.get
import keiyoushi.network.rateLimit
import okhttp3.HttpUrl.Companion.toHttpUrl
import okhttp3.OkHttpClient
import okhttp3.Request
import org.jsoup.Jsoup
import org.jsoup.nodes.Document
import org.jsoup.nodes.Element
import java.io.IOException
import kotlin.time.Duration.Companion.seconds

/**
 * XBL Black Paradise: Madara theme with custom 2026 catalogue/search cards,
 * season-aware chapter listing, and direct image extraction.
 * Source was checked against public HTML on 2026-11-14.
 * The XBL workflow applies the upstream formatter before assembling this module.
 */
@Source
abstract class BlackParadise : MadaraNoAjax() {
    override val supportsPostId = false
    override val mangaSubString = "manga"

    override fun OkHttpClient.Builder.configureClient() = rateLimit(2, 1.seconds) {
        !it.encodedPath.startsWith("/wp-content/uploads/")
    }

    private suspend fun document(url: String): Document {
        val response = client.get(url, Fetch.DOCUMENT, ensureSuccess = false)
        if (!response.isSuccessful) {
            throw IOException("Black Paradise: HTTP " + response.code + " ao acessar " + url)
        }
        return Jsoup.parse(response.body.string(), url)
    }

    override suspend fun getPopularManga(page: Int): MangasPage {
        val url = if (page == 1) "$baseUrl/manga/?m_orderby=latest"
            else "$baseUrl/manga/page/$page/?m_orderby=latest"
        val doc = document(url)
        val mangas = parseCards(doc)
        val next = doc.select("a.next.page-numbers, .pagination a.next, a[href*='/page/" + (page + 1) + "/']").isNotEmpty()
        return MangasPage(mangas, next)
    }

    override suspend fun getSearchMangaList(page: Int, query: String, filters: FilterList): MangasPage {
        if (query.isBlank()) return getPopularManga(page)
        if (page > 1) return MangasPage(emptyList(), false)
        val url = "$baseUrl/".toHttpUrl().newBuilder()
            .addQueryParameter("s", query.trim())
            .addQueryParameter("post_type", "wp-manga")
            .build().toString()
        return MangasPage(parseCards(document(url)), false)
    }

    private fun parseCards(doc: Document): List<SManga> {
        val cards = doc.select("article[class*='bp-generic-card-'], .page-item-detail.manga")
        return cards.mapNotNull { card ->
            val link = card.selectFirst("a[class*='bp-generic-title-'][href*='/manga/'], .post-title a[href*='/manga/']")
                ?: return@mapNotNull null
            val url = link.attr("abs:href")
            val name = link.text().trim()
            if (!url.startsWith(baseUrl + "/manga/") || name.isBlank()) return@mapNotNull null
            val cover = card.selectFirst("a[class*='bp-generic-cover-'] img, .item-thumb img, img")
            SManga.create().apply {
                setUrlWithoutDomain(url)
                title = name
                thumbnail_url = cover?.let(::imageAttribute)
            }
        }.distinctBy { it.url }
    }

    private fun imageAttribute(image: Element): String? =
        sequenceOf("data-src", "data-lazy-src", "data-original", "src")
            .map { image.attr("abs:" + it).trim() }
            .firstOrNull { it.startsWith("https://") || it.startsWith("http://") }

    override suspend fun fetchMangaUpdate(
        manga: SManga,
        chapters: List<SChapter>,
        fetchDetails: Boolean,
        fetchChapters: Boolean,
    ): SMangaUpdate {
        val doc = document(getMangaUrl(manga))
        val details = if (fetchDetails) manga.apply {
            title = doc.selectFirst(".post-title h1, h1")?.text()?.trim()?.ifBlank { title } ?: title
            thumbnail_url = doc.selectFirst(".summary_image img")?.let(::imageAttribute) ?: thumbnail_url
            description = doc.selectFirst(".bp-work-synopsis, .manga-excerpt.summary__content, .summary__content")
                ?.text()?.trim()?.takeIf { it.isNotBlank() } ?: description
            author = doc.selectFirst("[data-bp-work-field=author] .summary-content")
                ?.text()?.trim()?.takeIf { it.isNotBlank() } ?: author
            artist = doc.selectFirst("[data-bp-work-field=artist] .summary-content")
                ?.text()?.trim()?.takeIf { it.isNotBlank() } ?: artist
            genre = doc.select("a[href*='/manga-genre/']").eachText()
                .filter { it.isNotBlank() }.distinct().joinToString(", ")
                .takeIf { it.isNotBlank() } ?: genre
            val state = doc.selectFirst("[data-bp-work-field=status] .summary-content")
                ?.text()?.lowercase().orEmpty()
            status = when {
                state.contains("complet") || state.contains("conclu") -> SManga.COMPLETED
                state.contains("andamento") || state.contains("lançamento") -> SManga.ONGOING
                else -> status
            }
        } else manga

        val listed = if (fetchChapters) {
            // Native Madara links retain /season/ paths and correct ordering.
            val links = doc.select(".listing-chapters_wrap li.wp-manga-chapter > a[href]")
                .ifEmpty { doc.select("li.bp-chapters-redesign-item a.bp-chapters-redesign-link") }
            val found = links.mapNotNull { link ->
                val name = link.text().trim()
                val url = link.attr("abs:href")
                if (name.isBlank() || !url.startsWith(baseUrl + "/manga/")) null
                else SChapter.create().apply {
                    setUrlWithoutDomain(url)
                    this.name = name
                }
            }.distinctBy { it.url }
            if (found.isEmpty()) throw IOException("Black Paradise: não foi possível localizar os capítulos.")
            found
        } else chapters
        return SMangaUpdate(details, listed)
    }

    override fun getChapterUrl(chapter: SChapter): String {
        val path = chapter.url
        return when {
            path.startsWith("https://") || path.startsWith("http://") -> path
            path.startsWith("/manga/") -> baseUrl + path
            else -> super.getChapterUrl(chapter)
        }
    }

    override suspend fun getPageList(chapter: SChapter): List<Page> {
        val url = getChapterUrl(chapter)
        val doc = document(url)
        val images = doc.select(".reading-content img.wp-manga-chapter-img, .reading-content .page-break img")
            .mapNotNull(::imageAttribute)
            .distinct()
        if (images.isEmpty()) throw IOException("Black Paradise: imagens não encontradas. Abra o capítulo na WebView.")
        return images.mapIndexed { index, image -> Page(index, url, image) }
    }

    override fun getImageRequest(page: Page): Request = super.getImageRequest(page).newBuilder()
        .header("Referer", page.url.ifBlank { "$baseUrl/" })
        .build()
}
