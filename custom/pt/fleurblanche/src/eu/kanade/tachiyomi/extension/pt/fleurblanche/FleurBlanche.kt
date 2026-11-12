package eu.kanade.tachiyomi.extension.pt.fleurblanche

import eu.kanade.tachiyomi.multisrc.madara.MadaraNoAjax
import eu.kanade.tachiyomi.source.model.FilterList
import keiyoushi.annotation.Source
import keiyoushi.network.rateLimit
import okhttp3.Interceptor
import okhttp3.OkHttpClient
import okhttp3.Response
import java.io.IOException
import java.time.format.DateTimeFormatter
import java.util.Locale
import kotlin.time.Duration.Companion.seconds

/**
 * Fleur Blanche uses a working WordPress HTML search at
 * /?s=<query>&post_type=wp-manga, while its Madara AJAX archive
 * endpoint no longer returns reliable search results.
 *
 * MadaraNoAjax retains the shared Madara manga/chapter parsers and
 * retrieves search cards from HTML, resolving their manga IDs.
 */
@Source
abstract class FleurBlanche : MadaraNoAjax() {
    override val chapterDateFormat = DateTimeFormatter.ofPattern("dd/MM/yyyy", Locale.forLanguageTag("pt-BR"))
    override val chapterMode = ChapterMode.MangaAjax

    override fun OkHttpClient.Builder.configureClient() = addInterceptor(::authWarningIntercept)
        .rateLimit(1, 2.seconds) { !it.encodedPath.startsWith("/wp-content/uploads/") }

    override val mangaDetailsSelectorStatus = "div.post-content_item:contains(Status) > div.summary-content"

    // The site lists Master-Peace as "God's Peace" without that alternate name.
    // Handle the known alias before delegating to the site's HTML search.
    override suspend fun getSearchMangaList(page: Int, query: String, filters: FilterList) = super.getSearchMangaList(
        page,
        if (query.trim().replace(" ", "").replace("-", "").equals("masterpeace", ignoreCase = true)) "Peace" else query,
        filters,
    )

    private fun authWarningIntercept(chain: Interceptor.Chain): Response {
        val response = chain.proceed(chain.request())

        if (response.request.url.toString().contains("wp-login.php")) {
            response.close()
            throw IOException("É necessário realizar o login via WebView para acessar a fonte.")
        }

        return response
    }
}
