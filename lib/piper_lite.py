#!/usr/bin/env python3
"""piper_lite.py - run a Piper voice (.onnx + .onnx.json) without the piper-tts package.

Why: `pip install piper-tts` has to compile things and fails on Termux. This does the same job with
what Termux can install from its own repo:   pkg install python-numpy python-onnxruntime espeak

Usage (same flags as the real piper program, so Nebula can call either one):
    echo "Hello there" | python3 piper_lite.py --model voice.onnx --output_file out.wav
Options: --model/-m FILE   --output_file/--output-file/-f FILE   --speaker N   --length_scale X --noise_scale X --noise_w X
Exit codes: 0 ok, 2 missing dependency / model, 1 failed.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import wave


def die(msg, code=1):
    sys.stderr.write("piper_lite: %s\n" % msg)
    sys.exit(code)


def parse(argv):
    o = {"model": None, "out": None, "speaker": 0, "length": None, "noise": None, "noisew": None}
    i = 0
    while i < len(argv):
        a = argv[i]
        nxt = argv[i + 1] if i + 1 < len(argv) else None
        if a in ("--model", "-m"):
            o["model"] = nxt; i += 1
        elif a in ("--output_file", "--output-file", "-f"):
            o["out"] = nxt; i += 1
        elif a in ("--speaker", "-s"):
            o["speaker"] = int(nxt); i += 1
        elif a == "--length_scale":
            o["length"] = float(nxt); i += 1
        elif a == "--noise_scale":
            o["noise"] = float(nxt); i += 1
        elif a == "--noise_w":
            o["noisew"] = float(nxt); i += 1
        i += 1
    return o


def espeak_bin():
    for b in ("espeak-ng", "espeak"):
        p = shutil.which(b)
        if p:
            return p
    return None


def phonemize(text, voice):
    """Text -> IPA phonemes with espeak (what Piper voices were trained on)."""
    exe = espeak_bin()
    if not exe:
        die("espeak not found (pkg install espeak)", 2)
    out = subprocess.run([exe, "-q", "--ipa", "-v", voice, text], capture_output=True, text=True, timeout=30)
    ph = out.stdout.replace("\n", " ")
    ph = re.sub(r"_+", "", ph)          # espeak's separators
    ph = ph.replace("‍", "")
    return re.sub(r"\s+", " ", ph).strip()


def to_ids(phonemes, idmap):
    pad = idmap.get("_", [0])
    ids = list(idmap.get("^", [1]))
    for p in phonemes:
        if p in idmap:
            ids.extend(idmap[p])
            ids.extend(pad)
    ids.extend(idmap.get("$", [2]))
    return ids


def sentences(text):
    parts = re.split(r"(?<=[.!?;:])\s+", text.strip())
    return [p for p in parts if p.strip()]


def main():
    o = parse(sys.argv[1:])
    if not o["model"] or not os.path.isfile(o["model"]):
        die("--model FILE.onnx is required", 2)
    if not o["out"]:
        die("--output_file FILE.wav is required", 2)
    try:
        import numpy as np
        import onnxruntime as ort
    except ImportError as e:
        die("missing Python package (%s). Run: pkg install python-numpy python-onnxruntime" % e, 2)
    cfgf = o["model"] + ".json"
    if not os.path.isfile(cfgf):
        cfgf = os.path.splitext(o["model"])[0] + ".json"
    try:
        cfg = json.load(open(cfgf, encoding="utf-8"))
    except Exception as e:
        die("cannot read %s: %s" % (cfgf, e), 2)

    text = sys.stdin.read().strip()
    if not text:
        die("no text on stdin")
    rate = int(cfg.get("audio", {}).get("sample_rate", 22050))
    inf = cfg.get("inference", {})
    noise = o["noise"] if o["noise"] is not None else inf.get("noise_scale", 0.667)
    length = o["length"] if o["length"] is not None else inf.get("length_scale", 1.0)
    noisew = o["noisew"] if o["noisew"] is not None else inf.get("noise_w", 0.8)
    idmap = cfg.get("phoneme_id_map", {})
    voice = cfg.get("espeak", {}).get("voice", "en-us")
    multi = int(cfg.get("num_speakers", 1)) > 1

    so = ort.SessionOptions()
    so.intra_op_num_threads = max(1, min(4, os.cpu_count() or 2))
    sess = ort.InferenceSession(o["model"], sess_options=so, providers=["CPUExecutionProvider"])
    names = {i.name for i in sess.get_inputs()}

    chunks = []
    for sent in sentences(text):
        ph = phonemize(sent, voice) if cfg.get("phoneme_type", "espeak") != "text" else sent
        ids = to_ids(ph, idmap)
        if len(ids) < 3:
            continue
        feed = {
            "input": np.array([ids], dtype=np.int64),
            "input_lengths": np.array([len(ids)], dtype=np.int64),
            "scales": np.array([noise, length, noisew], dtype=np.float32),
        }
        if "sid" in names or multi:
            feed["sid"] = np.array([o["speaker"]], dtype=np.int64)
        audio = sess.run(None, feed)[0].squeeze()
        chunks.append(audio.astype(np.float32))
        chunks.append(np.zeros(int(rate * 0.12), dtype=np.float32))     # short pause between sentences
    if not chunks:
        die("nothing to say (no phonemes)")
    audio = np.concatenate(chunks)
    peak = max(0.01, float(np.abs(audio).max()))
    pcm = (audio * (32767.0 / max(0.01, peak * 1.0))).clip(-32767, 32767).astype(np.int16)
    with wave.open(o["out"], "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm.tobytes())


if __name__ == "__main__":
    main()
