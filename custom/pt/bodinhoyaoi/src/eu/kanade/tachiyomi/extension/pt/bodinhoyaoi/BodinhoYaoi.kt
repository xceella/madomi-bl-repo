package eu.kanade.tachiyomi.extension.pt.bodinhoyaoi

import eu.kanade.tachiyomi.source.model.FilterList
import eu.kanade.tachiyomi.source.model.MangasPage
import eu.kanade.tachiyomi.source.model.Page
import eu.kanade.tachiyomi.source.model.SChapter
import eu.kanade.tachiyomi.source.model.SManga
import eu.kanade.tachiyomi.source.model.SMangaUpdate
import keiyoushi.annotation.Source
import keiyoushi.network.get
import keiyoushi.source.KeiSource
import keiyoushi.utils.asJsoup
import okhttp3.HttpUrl.Companion.toHttpUrl
import org.jsoup.nodes.Document
import org.jsoup.nodes.Element

@Source
abstract class BodinhoYaoi : KeiSource() {

    override val supportsLatest = true

    override suspend fun getPopularManga(page: Int): MangasPage {
        val url = "$baseUrl/biblioteca".toHttpUrl().newBuilder()
            .addQueryParameter("page", page.toString())
            .build()
        return mangaListParse(client.get(url).asJsoup(), page)
    }

    override suspend fun getLatestUpdates(page: Int): MangasPage {
        val url = "$baseUrl/biblioteca".toHttpUrl().newBuilder()
            .addQueryParameter("order", "recent")
            .addQueryParameter("page", page.toString())
            .build()
        return mangaListParse(client.get(url).asJsoup(), page)
    }

    override suspend fun getSearchMangaList(page: Int, query: String, filters: FilterList): MangasPage {
        if (query.isBlank()) return getPopularManga(page)

        // The dynamic /busca route can intermittently stall long enough to hit
        // Madomi's 30 second source timeout. The sitemap is static, fast and
        // contains every work URL, so use it as the search index instead.
        val document = client.get("$baseUrl/sitemap.xml").asJsoup()
        return MangasPage(searchFromSitemap(document, query), false)
    }

    private fun searchFromSitemap(document: Document, query: String): List<SManga> {
        val normalizedQuery = query.trim().lowercase()
        val slugQuery = normalizedQuery
            .replace(Regex("[^\\p{L}\\p{N}]+"), "-")
            .trim('-')

        return document
            .select("loc")
            .map { it.text().trim() }
            .filter { it.contains("/obras/") && !it.contains("/capitulo/") }
            .distinct()
            .mapNotNull { url ->
                val slug = url.substringAfter("/obras/", "").substringBefore('/').trim()
                if (slug.isBlank()) return@mapNotNull null

                val searchableTitle = slug.replace('-', ' ').lowercase()
                val matches = slug.contains(slugQuery, ignoreCase = true) ||
                    searchableTitle.contains(normalizedQuery)
                if (!matches) return@mapNotNull null

                val title = slug
                    .split('-')
                    .filter { it.isNotBlank() }
                    .joinToString(" ") { word ->
                        word.replaceFirstChar { char ->
                            if (char.isLowerCase()) char.titlecase() else char.toString()
                        }
                    }

                SManga.create().apply {
                    setUrlWithoutDomain("/obras/$slug")
                    this.title = title
                    thumbnail_url = "https://media.bodinhoyaoi.com/$slug/cover-thumb.webp"
                }
            }
            .sortedBy { manga ->
                val slug = manga.url.substringAfterLast('/')
                if (slug.equals(slugQuery, ignoreCase = true)) 0 else 1
            }
    }

    private fun mangaListParse(document: Document, page: Int): MangasPage {
        val mangas = parseMangaCards(document)
        val hasNextPage = document.select("a[href*='page=${page + 1}']").isNotEmpty()
        return MangasPage(mangas, hasNextPage)
    }

    private fun parseMangaCards(document: Document): List<SManga> = document
        .select("a[href*='/obras/']:has(img[src*='media.bodinhoyaoi.com'])")
        .filterNot { it.attr("href").contains("/capitulo/") }
        .distinctBy { it.attr("abs:href").ifBlank { it.attr("href") } }
        .mapNotNull(::mangaFromElement)

    private fun mangaFromElement(element: Element): SManga? {
        val href = element.attr("abs:href").ifBlank { element.attr("href") }
        if (href.isBlank()) return null

        val image = element.selectFirst("img")
        val title = element.selectFirst("h1, h2, h3, strong")
            ?.text()
            ?.trim()
            ?.takeIf { it.isNotBlank() }
            ?: image?.attr("alt")
                ?.removePrefix("Capa de ")
                ?.trim()
                ?.takeIf { it.isNotBlank() }
            ?: return null

        return SManga.create().apply {
            setUrlWithoutDomain(href)
            this.title = title
            thumbnail_url = image?.attr("abs:src")?.takeIf { it.isNotBlank() }
        }
    }

    override suspend fun fetchMangaUpdate(
        manga: SManga,
        chapters: List<SChapter>,
        fetchDetails: Boolean,
        fetchChapters: Boolean,
    ): SMangaUpdate {
        val document = client.get(getMangaUrl(manga)).asJsoup()

        val updatedManga = if (fetchDetails) parseDetails(document, manga) else manga
        val updatedChapters = if (fetchChapters) parseChapters(document) else chapters

        return SMangaUpdate(updatedManga, updatedChapters)
    }

    private fun parseDetails(document: Document, original: SManga): SManga = original.apply {
        val titleElement = document.selectFirst("h1")
        title = titleElement?.text()?.takeIf { it.isNotBlank() } ?: title

        thumbnail_url = document.selectFirst("meta[property='og:image']")
            ?.attr("content")
            ?.takeIf { it.isNotBlank() }
            ?: thumbnail_url

        description = document.selectFirst("meta[name='description']")
            ?.attr("content")
            ?.takeIf { it.isNotBlank() }
            ?: description

        genre = document.select("a[href*='/biblioteca?genero=']")
            .map { it.text().trim() }
            .filter { it.isNotBlank() }
            .distinct()
            .joinToString(", ")
            .takeIf { it.isNotBlank() }
            ?: genre

        val statusText = titleElement
            ?.parent()
            ?.select("span")
            ?.map { it.text().trim() }
            ?.firstOrNull {
                it.equals("Completo", ignoreCase = true) ||
                    it.equals("Em andamento", ignoreCase = true)
            }

        status = when {
            statusText.equals("Completo", ignoreCase = true) -> SManga.COMPLETED
            statusText.equals("Em andamento", ignoreCase = true) -> SManga.ONGOING
            else -> status
        }

        author = findLabelValue(document, "Autor") ?: author
        artist = document.selectFirst("p:matchesOwn(^\\s*Arte:\\s*$) span")
            ?.text()
            ?.trim()
            ?.takeIf { it.isNotBlank() }
            ?: artist
    }

    private fun findLabelValue(document: Document, label: String): String? {
        val labelElement = document.selectFirst("*:matchesOwn(^\\s*$label\\s*$)") ?: return null
        val parent = labelElement.parent() ?: return null
        return parent.text()
            .removePrefix(label)
            .trim(' ', ':', '-', '–')
            .takeIf { it.isNotBlank() && !it.equals(label, ignoreCase = true) }
    }

    private fun parseChapters(document: Document): List<SChapter> = document
        .select("section[aria-labelledby='capitulos'] a[href*='/capitulo/']:has(span.block.truncate)")
        .distinctBy { it.attr("href") }
        .mapNotNull { element ->
            val href = element.attr("abs:href").ifBlank { element.attr("href") }
            if (href.isBlank()) return@mapNotNull null

            val slug = href.substringAfterLast("/capitulo/", "")
            val chapterTitle = element.selectFirst("span.block.truncate")
                ?.text()
                ?.trim()
                ?.takeIf { it.isNotBlank() }
                ?: "Capítulo $slug"

            SChapter.create().apply {
                setUrlWithoutDomain(href)
                name = chapterTitle
            }
        }

    override suspend fun getPageList(chapter: SChapter): List<Page> {
        val document = client.get(getChapterUrl(chapter)).asJsoup()
        return document
            .select("img[src*='media.bodinhoyaoi.com'][src*='/chapters/']")
            .distinctBy { it.attr("src") }
            .mapIndexed { index, element ->
                Page(index, imageUrl = element.attr("abs:src"))
            }
    }
}
