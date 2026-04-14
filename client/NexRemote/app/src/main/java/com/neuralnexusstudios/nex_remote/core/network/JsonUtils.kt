package com.neuralnexusstudios.nex_remote.core.network

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonNull
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.booleanOrNull
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.doubleOrNull
import kotlinx.serialization.json.intOrNull
import kotlinx.serialization.json.jsonPrimitive

val JsonCodec = Json {
    ignoreUnknownKeys = true
    prettyPrint = true
}

fun mapToJsonObject(values: Map<String, Any?>): JsonObject =
    JsonObject(values.mapValues { (_, value) -> value.toJsonElement() })

private fun Any?.toJsonElement(): JsonElement = when (this) {
    null -> JsonNull
    is JsonElement -> this
    is String -> JsonPrimitive(this)
    is Boolean -> JsonPrimitive(this)
    is Int -> JsonPrimitive(this)
    is Long -> JsonPrimitive(this)
    is Float -> JsonPrimitive(this)
    is Double -> JsonPrimitive(this)
    is Number -> JsonPrimitive(this)
    is Map<*, *> -> JsonObject(entries.associate { (key, value) -> key.toString() to value.toJsonElement() })
    is Iterable<*> -> JsonArray(map { it.toJsonElement() })
    is Array<*> -> JsonArray(map { it.toJsonElement() })
    else -> JsonPrimitive(toString())
}

fun JsonObject.string(name: String): String? = this[name]?.jsonPrimitive?.contentOrNull
fun JsonObject.int(name: String): Int? = this[name]?.jsonPrimitive?.intOrNull
fun JsonObject.double(name: String): Double? = this[name]?.jsonPrimitive?.doubleOrNull
fun JsonObject.bool(name: String): Boolean? = this[name]?.jsonPrimitive?.booleanOrNull
