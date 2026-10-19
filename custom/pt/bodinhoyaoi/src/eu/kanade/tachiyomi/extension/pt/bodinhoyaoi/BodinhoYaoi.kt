package eu.kanade.tachiyomi.extension.pt.bodinhoyaoi

import eu.kanade.tachiyomi.source.model.FilterList
import eu.kanade.tachiyomi.source.model.MangasPage
import eu.kanade.tachiyomi.source.model.Page
import eu.kanade.tachiyomi.source.model.SChapter
import eu.kanade.tachiyomi.source.model.SManga
import eu.kanade.tachiyomi.source.model.SMangaUpdate
import keiyoushi.annotation.Source
import keiyoushi.network.get
import keiyoushi.network.head
import keiyoushi.source.KeiSource
import keiyoushi.utils.asJsoup
import keiyoushi.utils.runWebView
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.selects.select
import okhttp3.HttpUrl.Companion.toHttpUrl
import okhttp3.Request
import org.jsoup.Jsoup
import org.jsoup.nodes.Document
import org.jsoup.nodes.Element
import java.io.IOException
import kotlin.time.Duration.Companion.seconds

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
        val chapterUrl = getChapterUrl(chapter)
        var httpDiagnostic = "requisição não concluída"
        var initialHtml: String? = null

        // Match the browser-style document headers from our working XXX Yaoi source.
        val pageHeaders = headers.newBuilder()
            .set("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")
            .set("Upgrade-Insecure-Requests", "1")
            .set("Sec-Fetch-Site", "none")
            .set("Sec-Fetch-Mode", "navigate")
            .set("Sec-Fetch-Dest", "document")
            .set("Sec-Fetch-User", "?1")
            .build()

        val directPages = try {
            val response = client.get(chapterUrl, pageHeaders, ensureSuccess = false)
            val html = response.body.string()
            initialHtml = html
            val document = Jsoup.parse(html, chapterUrl)
            httpDiagnostic = "HTTP${response.code}/${html.length}, imgs=${document.select("img").size}, ref=${html.contains("/chapters/")}"
            extractChapterPages(document, chapterUrl)
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            httpDiagnostic = "${e.javaClass.simpleName}: ${e.message?.take(28).orEmpty()}"
            emptyList()
        }
        if (directPages.isNotEmpty()) return directPages

        // Adapt the XXX Yaoi technique: render the already-fetched document.
        // Next.js scripts remain available; image downloads are blocked.
        // Concurrent fallback avoids adding WebView timeout to CDN probing.
        var browserDiagnostic = "não iniciado"
        var cdnDiagnostic = "não iniciado"

        return coroutineScope {
            val browserTask = async {
                try {
                    val rendered = runWebView<String>(7.seconds) {
                        userAgent = headers["User-Agent"].orEmpty()
                        blockImages = true
                        jsBridge("xblBodinhoHtml") { resolve(it) }
                        onPageFinished {
                            evaluateJs(
                                """
                                (function() {
                                  if (window.__xblReaderProbeInstalled) return;
                                  window.__xblReaderProbeInstalled = true;
                                  var attempts = 0;
                                  function extract() {
                                    var images = document.querySelectorAll(
                                      "img[src*='/chapters/'], img[data-src*='/chapters/'], img[data-lazy-src*='/chapters/']"
                                    );
                                    if (images.length > 0 || ++attempts >= 12) {
                                      xblBodinhoHtml.post(document.documentElement.outerHTML);
                                    } else {
                                      setTimeout(extract, 250);
                                    }
                                  }
                                  extract();
                                })();
                                """.trimIndent(),
                            )
                        }
                        if (initialHtml != null) {
                            loadData(chapterUrl, initialHtml!!)
                        } else {
                            loadUrl(chapterUrl)
                        }
                    }
                    val document = Jsoup.parse(rendered, chapterUrl)
                    val pages = extractChapterPages(document, chapterUrl)
                    browserDiagnostic = "html=${rendered.length}, imgs=${document.select("img").size}, pages=${pages.size}"
                    pages
                } catch (e: CancellationException) {
                    throw e
                } catch (e: Exception) {
                    browserDiagnostic = "${e.javaClass.simpleName}: ${e.message?.take(28).orEmpty()}"
                    emptyList()
                }
            }

            val cdnTask = async(Dispatchers.IO) {
                try {
                    discoverMediaPages(chapter, chapterUrl).also {
                        cdnDiagnostic = "pages=${it.size}"
                    }
                } catch (e: CancellationException) {
                    throw e
                } catch (e: Exception) {
                    cdnDiagnostic = "${e.javaClass.simpleName}: ${e.message?.take(28).orEmpty()}"
                    emptyList()
                }
            }

            val first = select<Pair<Boolean, List<Page>>> {
                browserTask.onAwait { true to it }
                cdnTask.onAwait { false to it }
            }
            if (first.second.isNotEmpty()) {
                if (first.first) cdnTask.cancel() else browserTask.cancel()
                first.second
            } else {
                val remaining = if (first.first) cdnTask.await() else browserTask.await()
                if (remaining.isNotEmpty()) {
                    remaining
                } else {
                    throw IOException(
                        "Bodinho v1.6.11: direto=$httpDiagnostic; CDN=$cdnDiagnostic; web=$browserDiagnostic; sem imagens.",
                    )
                }
            }
        }
    }

    private fun extractChapterPages(document: Document, chapterUrl: String): List<Page> {
        // Include preload links, Next.js hydration data and normal <img> elements.
        // Some requests return URLs escaped as \u002F or \/ instead of literal slashes.
        val normalizedHtml = document.html()
            .replace("\\u002F", "/")
            .replace("\\u002f", "/")
            .replace("\\/", "/")
            .replace("\\\"", "\"")
            .replace("&#x2F;", "/")
            .replace("&quot;", "\"")

        val chapterImagePattern = Regex(
            """https?://media\.bodinhoyaoi\.com/[^"'<>\\\s]+?\.(?:jpe?g|png|webp|avif)(?:\?[^"'<>\s\\]*)?""",
            RegexOption.IGNORE_CASE,
        )

        val urls = chapterImagePattern.findAll(normalizedHtml)
            .map { it.value }
            .filter { it.contains("/chapters/", ignoreCase = true) }
            .distinct()
            .toList()

        return urls.mapIndexed { index, url -> Page(index, chapterUrl, url) }
    }

    /**
     * Fast CDN fallback for reader HTML missing the chapter image URLs.
     * Probe four page numbers concurrently instead of waiting sequentially for
     * every jpg/webp HEAD response. Never download the actual image here.
     * Preserve contiguous ordering and stop at the first missing page.
     */
    private suspend fun discoverMediaPages(chapter: SChapter, chapterUrl: String): List<Page> {
        val bookSlug = chapter.url.substringAfter("/obras/", "").substringBefore('/')
        val chapterSlug = chapter.url.substringAfter("/capitulo/", "").substringBefore('/').substringBefore('?')

        if (!bookSlug.matches(Regex("[a-z0-9-]+")) || !chapterSlug.matches(Regex("[0-9]+(?:\\.[0-9]+)?"))) {
            return emptyList()
        }

        val mediaHeaders = headers.newBuilder().set("Referer", chapterUrl).build()
        val results = mutableListOf<Page>()

        suspend fun probePage(pageNumber: Int): String? {
            val filename = pageNumber.toString().padStart(4, '0')
            val prefix = "https://media.bodinhoyaoi.com/$bookSlug/chapters/$chapterSlug/$filename"

            suspend fun isImage(extension: String): Boolean = try {
                client.head("$prefix.$extension", mediaHeaders, ensureSuccess = false).use { response ->
                    response.isSuccessful && response.header("Content-Type").orEmpty().startsWith("image/", ignoreCase = true)
                }
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                false
            }

            // Both formats occur within the same chapter, so test them in parallel.
            val primary = coroutineScope {
                listOf("jpg", "webp").map { extension ->
                    async(Dispatchers.IO) { extension to isImage(extension) }
                }.awaitAll().firstOrNull { (_, exists) -> exists }?.first
            }
            if (primary != null) return "$prefix.$primary"

            // Less common extensions, also concurrently, only if both above fail.
            val secondary = coroutineScope {
                listOf("png", "jpeg", "avif").map { extension ->
                    async(Dispatchers.IO) { extension to isImage(extension) }
                }.awaitAll().firstOrNull { (_, exists) -> exists }?.first
            }
            return secondary?.let { "$prefix.$it" }
        }

        // Four pages per batch bounds concurrent HEAD requests and avoids
        // probing the entire chapter before discovering its end.
        for (start in 1..80 step 4) {
            val batch = coroutineScope {
                (start..minOf(start + 3, 80)).map { pageNumber ->
                    async(Dispatchers.IO) { probePage(pageNumber) }
                }.awaitAll()
            }
            for (url in batch) {
                if (url == null) return results
                results.add(Page(results.size, chapterUrl, url))
            }
        }
        return results
    }

    override fun imageRequest(page: Page): Request = super.imageRequest(page).newBuilder()
        .header("Referer", page.url.ifBlank { "$baseUrl/" })
        .build()
}
