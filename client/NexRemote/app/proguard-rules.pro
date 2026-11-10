# NexRemote R8 rules. Keep these narrow and add one only for a proven shrinker breakage.

# ML Kit code scanner (play-services-code-scanner). Its client wires itself up through
# components that are found by reflection; with R8 full mode the release build crashed with
# an NPE in com.google.android.gms.internal.mlkit_code_scanner as soon as the scanner client
# was created (1.3.0, Samsung Galaxy A6+, Android 10). Debug builds were unaffected.
-keep class com.google.mlkit.vision.codescanner.** { *; }
-keep class com.google.android.gms.internal.mlkit_code_scanner.** { *; }
-keep class com.google.mlkit.common.internal.** { *; }
-keep class com.google.mlkit.common.sdkinternal.** { *; }
