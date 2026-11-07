"""Independent v1 recipes for the small single-segment public client fixture."""
import hashlib
import json

SCHEMA = "mousa.source_manifest.v1"
SELECTOR = "mousa.selector.text_byte_range.v1"
ITEM_FIELDS = ("item", "observation_id", "artifact_id", "representation_id", "raw_sha256",
               "raw_byte_length", "normalized_sha256", "normalized_byte_length", "processor_id",
               "processor_version", "parameters_sha256", "segmentation_policy", "segment_count",
               "segments_sha256")


def sha(value):
    return hashlib.sha256(value).hexdigest()


def encoded(value):
    # Go's non-HTML-escaped encoder retains U+2028/U+2029 escaping and a final LF.
    text = json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return (text.replace("\u2028", "\\u2028").replace("\u2029", "\\u2029") + "\n").encode()


def identity(*fields):
    fields = [field.encode() if isinstance(field, str) else field for field in fields]
    return sha(b"".join(len(field).to_bytes(8, "big") + field for field in fields))


def manifest_id(record):
    rows = [{key: item[key] for key in ITEM_FIELDS} for item in record["items"]]
    return identity(SCHEMA, encoded(dict(source_id=record["source_id"], items=rows)))


def expected(source, texts, policy="fixed-v1"):
    source_id = identity("mousa.source.v1", "mousa-jsonl", source)
    parameters = sha(b"" if policy == "fixed-v1" else b'{"segmentation":"passage-v1"}')
    rows, inventory = [], {}
    for item, text in sorted(texts.items(), key=lambda pair: pair[0].encode()):
        raw = text.encode()
        normalized = raw.removeprefix(b"\xef\xbb\xbf").replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        if len(normalized) > 1024 or b"\n\n" in normalized:
            raise ValueError("fixture requires at most one short paragraph per item")
        # The local adapter formats SHA256's hexadecimal String value with %x.
        observation_key = "item/" + item + "@" + sha(raw).encode().hex()
        observation = identity("mousa.observation.v1", bytes.fromhex(source_id), observation_key)
        artifact = identity("mousa.artifact.v1", bytes.fromhex(observation), "body")
        representation = identity("mousa.representation.v1", (1).to_bytes(8, "big"), "artifact",
                                  bytes.fromhex(artifact), "mousa.text.normalize_utf8", "1",
                                  bytes.fromhex(parameters), "text/plain; charset=utf-8", bytes.fromhex(sha(normalized)))
        segments = []
        if normalized:
            segment = identity("mousa.segment.v1", bytes.fromhex(representation), SELECTOR,
                               (0).to_bytes(8, "big"), len(normalized).to_bytes(8, "big"), bytes.fromhex(sha(normalized)))
            segments.append(dict(segment_id=segment, selector=dict(schema=SELECTOR, start=0, end=len(normalized)),
                                 content_sha256=sha(normalized)))
        inventory[item] = segments
        rows.append(dict(item=item, observation_id=observation, artifact_id=artifact,
                         representation_id=representation, raw_sha256=sha(raw), raw_byte_length=len(raw),
                         normalized_sha256=sha(normalized), normalized_byte_length=len(normalized),
                         processor_id="mousa.text.normalize_utf8", processor_version="1",
                         parameters_sha256=parameters, segmentation_policy=policy, segment_count=len(segments),
                         segments_sha256=identity("mousa.source_manifest_segments.v1", encoded(segments))))
    record = dict(schema=SCHEMA, id="", source_id=source_id, items=rows)
    record["id"] = manifest_id(record)
    return record, inventory
