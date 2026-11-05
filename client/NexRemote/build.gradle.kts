// AGP 9 compiles Kotlin with the Kotlin Gradle plugin on this classpath. Pin it to the catalog's
// Kotlin so the compiler can read com.composables:ui (built with Kotlin 2.4).
buildscript {
    dependencies {
        classpath(libs.kotlin.gradle.plugin)
    }
}

// Top-level build file where you can add configuration options common to all sub-projects/modules.
plugins {
    alias(libs.plugins.android.application) apply false
}