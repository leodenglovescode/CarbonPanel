package dev.carbonpanel.ui

import kotlinx.coroutines.flow.MutableStateFlow

/**
 * Loading state for anything fetched on demand.
 *
 * Every list screen needs the same three states, and repeating a
 * `data/loading/error` triple per feature in the ViewModel was most of its
 * bulk. [Ok] keeps the previous value visible during a refresh so pull-to-
 * refresh doesn't blank the screen.
 */
sealed interface Load<out T> {
    data object Loading : Load<Nothing>
    data class Ok<T>(val data: T, val refreshing: Boolean = false) : Load<T>
    data class Err(val message: String) : Load<Nothing>

    val dataOrNull: T? get() = (this as? Ok)?.data
}

/** Marks a flow as refreshing without discarding what's already on screen. */
fun <T> MutableStateFlow<Load<T>>.markRefreshing() {
    val current = value
    if (current is Load.Ok) value = current.copy(refreshing = true)
}

/** Applies a repository Result to this flow. */
fun <T> MutableStateFlow<Load<T>>.applyResult(result: Result<T>) {
    value = result.fold(
        onSuccess = { Load.Ok(it) },
        onFailure = { Load.Err(it.message ?: "Request failed") },
    )
}
