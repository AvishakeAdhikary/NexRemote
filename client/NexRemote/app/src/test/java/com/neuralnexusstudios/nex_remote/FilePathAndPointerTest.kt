package com.neuralnexusstudios.nex_remote

import com.google.common.truth.Truth.assertThat
import com.neuralnexusstudios.nex_remote.ui.screens.breadcrumbsOf
import com.neuralnexusstudios.nex_remote.ui.screens.parentPathOf
import com.neuralnexusstudios.nex_remote.ui.screens.pointerGain
import org.junit.Test

class FilePathAndPointerTest {
    @Test
    fun parentOfNestedFolderIsItsContainingFolder() {
        assertThat(parentPathOf("C:\\Users\\me\\Documents")).isEqualTo("C:\\Users\\me")
        assertThat(parentPathOf("C:\\Users\\me\\Documents\\")).isEqualTo("C:\\Users\\me")
        assertThat(parentPathOf("C:\\Users")).isEqualTo("C:\\")
        assertThat(parentPathOf("D:\\Games")).isEqualTo("D:\\")
    }

    @Test
    fun driveRootHasNoParent() {
        assertThat(parentPathOf("C:\\")).isNull()
        assertThat(parentPathOf("C:")).isNull()
        assertThat(parentPathOf("")).isNull()
    }

    @Test
    fun breadcrumbsBuildClickablePaths() {
        assertThat(breadcrumbsOf("C:\\Users\\me")).containsExactly(
            "C:" to "C:\\",
            "Users" to "C:\\Users",
            "me" to "C:\\Users\\me",
        ).inOrder()
        assertThat(breadcrumbsOf("C:\\")).containsExactly("C:" to "C:\\")
    }

    @Test
    fun pointerAccelerationIsMonotonicAndBounded() {
        val slow = pointerGain(0.1f, 1f)
        val medium = pointerGain(1f, 1f)
        val fast = pointerGain(5f, 1f)
        assertThat(slow).isLessThan(medium)
        assertThat(medium).isLessThan(fast)
        assertThat(slow).isAtLeast(1f) // never slower than the finger
        assertThat(fast).isAtMost(3.6f)
        assertThat(pointerGain(1f, 2f)).isEqualTo(pointerGain(1f, 1f) * 2f)
    }
}
