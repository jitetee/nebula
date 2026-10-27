#!/usr/bin/env python3
"""piper_lite.py - run a Piper voice (.onnx + .onnx.json) without the piper-tts package.

Why: `pip install piper-tts` has to compile things and fails on Termux. This does the same job with
what Termux can install from its own repo:   pkg install python-numpy python-onnxruntime espeak

Usage (same flags as the real piper program, so Nebula can call either one):
    echo "Hello there" | python3 piper_lite.py --model voice.onnx --output_file out.wav
Options: --model/-m FILE   --output_file/--output-file/-f FILE   --speaker N   --length_scale X --noise_scale X --noise_w X

Fast mode (what Nebula uses): the model is loaded ONCE and kept in a small background server, so after the
first phrase there is no start-up cost, and long text is spoken sentence by sentence while the next sentence
is still being made.
    python3 piper_lite.py --serve SOCKET [--idle 900]          start the server (loads the model on first request)
    echo "Hello" | python3 piper_lite.py --say SOCKET --model voice.onnx --cache DIR
        prints the path of each finished .wav, one per line, as soon as it is ready
Exit codes: 0 ok, 2 missing dependency / model, 1 failed.
"""
import json
import os
import re
import shutil
import hashlib
import socket
import subprocess
import sys
import time
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


class Voice:
    """One loaded model. Heavy imports happen here so the client path stays fast."""

    def __init__(self, model):
        try:
            import numpy as np
            import onnxruntime as ort
        except ImportError as e:
            die("missing Python package (%s). Run: pkg install python-numpy python-onnxruntime" % e, 2)
        self.np = np
        self.model = model
        cfgf = model + ".json"
        if not os.path.isfile(cfgf):
            cfgf = os.path.splitext(model)[0] + ".json"
        try:
            self.cfg = json.load(open(cfgf, encoding="utf-8"))
        except Exception as e:
            die("cannot read %s: %s" % (cfgf, e), 2)
        so = ort.SessionOptions()
        so.intra_op_num_threads = max(1, min(4, os.cpu_count() or 2))
        so.add_session_config_entry("session.intra_op.allow_spinning", "0")
        self.sess = ort.InferenceSession(model, sess_options=so, providers=["CPUExecutionProvider"])
        self.names = {i.name for i in self.sess.get_inputs()}
        a = self.cfg.get("audio", {})
        self.rate = int(a.get("sample_rate", 22050))
        inf = self.cfg.get("inference", {})
        self.noise = inf.get("noise_scale", 0.667)
        self.length = inf.get("length_scale", 1.0)
        self.noisew = inf.get("noise_w", 0.8)
        self.idmap = self.cfg.get("phoneme_id_map", {})
        self.evoice = self.cfg.get("espeak", {}).get("voice", "en-us")
        self.multi = int(self.cfg.get("num_speakers", 1)) > 1

    def synth(self, sentence, speaker=0, length=None, noise=None, noisew=None):
        np = self.np
        ph = phonemize(sentence, self.evoice) if self.cfg.get("phoneme_type", "espeak") != "text" else sentence
        ids = to_ids(ph, self.idmap)
        if len(ids) < 3:
            return None
        feed = {
            "input": np.array([ids], dtype=np.int64),
            "input_lengths": np.array([len(ids)], dtype=np.int64),
            "scales": np.array([self.noise if noise is None else noise, self.length if length is None else length,
                                self.noisew if noisew is None else noisew], dtype=np.float32),
        }
        if "sid" in self.names or self.multi:
            feed["sid"] = np.array([speaker], dtype=np.int64)
        audio = self.sess.run(None, feed)[0].squeeze().astype(np.float32)
        peak = max(0.01, float(np.abs(audio).max()))
        pcm = (audio * (32767.0 / peak)).clip(-32767, 32767).astype(np.int16)
        pause = np.zeros(int(self.rate * 0.10), dtype=np.int16)
        return np.concatenate([pcm, pause])

    def write_wav(self, path, pcm):
        tmp = path + ".part"
        with wave.open(tmp, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(self.rate)
            w.writeframes(pcm.tobytes())
        os.replace(tmp, path)


def wav_path(cache, model, sentence):
    k = hashlib.sha1((model + "|" + sentence).encode("utf-8")).hexdigest()[:20]
    return os.path.join(cache, k + ".wav")


# ── server ───────────────────────────────────────────────────────────────
def serve(sock_path, idle):
    voice = None
    if os.path.exists(sock_path):
        os.unlink(sock_path)
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(sock_path)
    os.chmod(sock_path, 0o600)
    srv.listen(4)
    last = time.time()
    srv.settimeout(5)
    while time.time() - last < idle:
        try:
            conn, _ = srv.accept()
        except socket.timeout:
            continue
        last = time.time()
        try:
            f = conn.makefile("rwb")
            req = json.loads(f.readline().decode("utf-8"))
            model, cache = req["model"], req["cache"]
            os.makedirs(cache, exist_ok=True)
            if voice is None or voice.model != model:
                voice = Voice(model)
            for sent in sentences(req["text"]):
                p = wav_path(cache, model, sent)
                if not os.path.isfile(p):
                    pcm = voice.synth(sent)
                    if pcm is None:
                        continue
                    voice.write_wav(p, pcm)
                f.write((p + "\n").encode("utf-8"))
                f.flush()
            f.write(b"END\n")
            f.flush()
        except Exception as e:                      # one bad request must not kill the server
            try:
                conn.sendall(("ERR %s\nEND\n" % e).encode("utf-8"))
            except Exception:
                pass
        finally:
            conn.close()
            last = time.time()
    try:
        os.unlink(sock_path)
    except OSError:
        pass


def say(sock_path, model, cache, text):
    """Client: stdlib only, starts instantly."""
    c = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    c.settimeout(120)
    c.connect(sock_path)
    f = c.makefile("rwb")
    f.write((json.dumps({"model": model, "cache": cache, "text": text}) + "\n").encode("utf-8"))
    f.flush()
    rc = 0
    for line in f:
        line = line.decode("utf-8").rstrip("\n")
        if line == "END":
            break
        if line.startswith("ERR"):
            sys.stderr.write("piper_lite: %s\n" % line[4:])
            rc = 1
            continue
        print(line, flush=True)
    return rc


def main():
    argv = sys.argv[1:]
    if "--serve" in argv:
        i = argv.index("--serve")
        idle = float(argv[argv.index("--idle") + 1]) if "--idle" in argv else 900.0
        serve(argv[i + 1], idle)
        return
    if "--say" in argv:
        o = parse(argv)
        sock = argv[argv.index("--say") + 1]
        cache = argv[argv.index("--cache") + 1] if "--cache" in argv else "/tmp/nebula-voice-cache"
        text = sys.stdin.read().strip()
        if not text or not o["model"]:
            die("--model and text on stdin are required", 2)
        try:
            sys.exit(say(sock, o["model"], cache, text))
        except (ConnectionError, FileNotFoundError, socket.timeout) as e:
            die("server not reachable: %s" % e, 3)
    o = parse(argv)
    if not o["model"] or not os.path.isfile(o["model"]):
        die("--model FILE.onnx is required", 2)
    if not o["out"]:
        die("--output_file FILE.wav is required", 2)
    text = sys.stdin.read().strip()
    if not text:
        die("no text on stdin")
    v = Voice(o["model"])
    parts = []
    for sent in sentences(text):
        pcm = v.synth(sent, o["speaker"], o["length"], o["noise"], o["noisew"])
        if pcm is not None:
            parts.append(pcm)
    if not parts:
        die("nothing to say (no phonemes)")
    v.write_wav(o["out"], v.np.concatenate(parts))


if __name__ == "__main__":
    main()
