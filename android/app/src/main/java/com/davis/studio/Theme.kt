package com.davis.studio

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Shapes
import androidx.compose.material3.darkColorScheme
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp

val Ink = Color(0xFF0B1014)
val Panel = Color(0xFF151C22)
val PanelHigh = Color(0xFF1E2830)
val Line = Color(0xFF2A3640)
val Mint = Color(0xFF25D366)
val MintDark = Color(0xFF04210F)
val Amber = Color(0xFFFFC857)
val Danger = Color(0xFFFF6B6B)
val TextHigh = Color(0xFFE9EDEF)
val TextLow = Color(0xFF8B9AA5)

private val DavisColors = darkColorScheme(
    primary = Mint,
    onPrimary = MintDark,
    primaryContainer = Color(0xFF0F3D24),
    onPrimaryContainer = Color(0xFFB8F5CF),
    secondary = Amber,
    onSecondary = Color(0xFF2B1F00),
    secondaryContainer = PanelHigh,
    onSecondaryContainer = TextHigh,
    background = Ink,
    onBackground = TextHigh,
    surface = Ink,
    onSurface = TextHigh,
    surfaceVariant = Panel,
    onSurfaceVariant = TextLow,
    surfaceContainer = Panel,
    surfaceContainerHigh = PanelHigh,
    surfaceContainerHighest = PanelHigh,
    surfaceContainerLow = Panel,
    outline = Line,
    outlineVariant = Line,
    error = Danger,
    onError = Color(0xFF2B0000),
)

private val DavisShapes = Shapes(
    small = RoundedCornerShape(10.dp),
    medium = RoundedCornerShape(16.dp),
    large = RoundedCornerShape(22.dp),
)

@Composable
fun DavisTheme(content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = DavisColors, shapes = DavisShapes, content = content)
}
