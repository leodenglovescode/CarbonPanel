package dev.carbonpanel.ui.components

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyListScope
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import dev.carbonpanel.ui.Load

/**
 * Standard list screen: pull-to-refresh, and one place that renders the
 * loading / error / empty states so no screen invents its own.
 *
 * [Load.Ok] with `refreshing` keeps existing content on screen during a
 * refresh — blanking a list the user is reading to show a spinner is a
 * regression they can feel.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun <T> LoadList(
    state: Load<List<T>>,
    onRefresh: () -> Unit,
    emptyTitle: String,
    emptyDetail: String? = null,
    modifier: Modifier = Modifier,
    header: (LazyListScope.() -> Unit)? = null,
    itemContent: LazyListScope.(List<T>) -> Unit,
) {
    val refreshing = (state as? Load.Ok)?.refreshing == true

    PullToRefreshBox(
        isRefreshing = refreshing,
        onRefresh = onRefresh,
        modifier = modifier.fillMaxSize(),
    ) {
        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            contentPadding = PaddingValues(12.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            header?.invoke(this)
            when (state) {
                is Load.Loading -> item { LoadingBlock() }
                is Load.Err -> item { ErrorBanner(state.message) }
                is Load.Ok -> {
                    if (state.data.isEmpty()) {
                        item { EmptyState(emptyTitle, emptyDetail) }
                    } else {
                        itemContent(state.data)
                    }
                }
            }
        }
    }
}

/** Same states, for a screen that isn't a list. */
@Composable
fun <T> LoadContent(
    state: Load<T>,
    modifier: Modifier = Modifier,
    content: @Composable (T) -> Unit,
) {
    Box(modifier) {
        when (state) {
            is Load.Loading -> LoadingBlock()
            is Load.Err -> ErrorBanner(state.message)
            is Load.Ok -> content(state.data)
        }
    }
}
