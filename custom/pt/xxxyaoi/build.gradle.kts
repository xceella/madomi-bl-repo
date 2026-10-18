import io.github.keiyoushi.gradle.api.ContentWarning

plugins {
    alias(kei.plugins.extension)
}

keiyoushi {
    name = "XXX Yaoi"
    // Custom XBL fix for the current chapter-list layout, based on Keiyoushi XXXYaoi.
    versionCode = 6
    contentWarning = ContentWarning.NSFW
    libVersion = "1.6"
    theme = "madara"

    source {
        lang = "pt-BR"
        baseUrl = "https://3xyaoi.com"
    }
}
