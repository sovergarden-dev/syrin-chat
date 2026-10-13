# -*- coding: utf-8 -*-
"""
Mini-benchmark OCR tiếng Việt cho Auto-Chat Agent (Phase 0 spike).
- Chế độ synthetic: tự sinh ảnh dòng chat (nền chat app tối, nền game nhiễu, chữ nhỏ) rồi đo CER.
- Chế độ dataset: --dataset DIR chứa ảnh + labels.tsv (tên_file<TAB>nhãn) để chạy trên ảnh thật của bạn.
Chỉ số: CER (có dấu, NFC), CER_bỏ_dấu, tỉ lệ dòng đúng 100%, "trần từ điển" (% ký tự GT không có trong dict), latency.
"""
import argparse, csv, glob, os, random, statistics, sys, time, unicodedata as ud
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter

LINES = [
 "Chào bạn, tối nay đi phó bản không?", "Mình đang bận, chút nữa nhắn lại nhé.",
 "[Tổ đội] Minh Tuấn: ai có bình máu cho mượn với", "Ủa sao hôm qua không vào trận vậy?",
 "Đừng quên mang theo giấy tờ tùy thân nha.", "Trận này khó quá, mình thua ba lần rồi.",
 "Nhớ gửi báo cáo trước thứ Sáu giúp anh.", "Hướng dẫn tân thủ ở kênh thế giới đó.",
 "Được rồi, để tôi kiểm tra lại đơn hàng.", "[Bang hội] Ngọc Ánh: tối nay đánh boss lúc 9 giờ",
 "Cảm ơn nhiều nhé, hẹn gặp lại cuối tuần!", "Sao cậu không trả lời tin nhắn của tớ?",
 "Ừ, để mai mình chuyển khoản cho.", "Bọn mình thiếu một người hỗ trợ, ai vào không?",
 "Đội trưởng ơi, cho em xin lời mời với ạ.", "Nghỉ ngơi đi, mai còn phải dậy sớm đấy.",
 "Tướng này mạnh thật, nhưng hơi khó chơi.", "Quà sự kiện hôm nay là trang phục mới.",
 "Bạn ở khu vực nào? Mình ở Đà Nẵng.", "Lỗi kết nối rồi, đợi mình khởi động lại máy.",
 "Thôi chết, mình quên mất cuộc họp lúc ba giờ.", "Ai bán kiếm cấp 60 không? Mình trả giá cao.",
 "Đã nhận được tài liệu, cảm ơn chị nhiều.", "Chơi tiếp không hay nghỉ ở đây luôn?",
 "Giữ vị trí đường giữa, đừng đẩy lẻ nữa!", "Hôm nay trời mưa to quá, ở nhà thôi.",
 "Kỹ năng cuối của tướng này hồi chiêu lâu lắm.", "Mình gửi lời mời kết bạn rồi đó, chấp nhận nhé.",
 "Ủng hộ đội mình một lượt thích nha mọi người.", "Vừa lên cấp, giờ đi làm nhiệm vụ chính tuyến.",
 "Đường truyền chậm quá, giật lag liên tục.", "Em xin phép về sớm hôm nay ạ.",
 "Mấy giờ thì bắt đầu sự kiện săn rồng?", "Tuyệt vời! Chúng ta thắng rồi!",
 "Phần thưởng chia đều cho cả đội nhé.", "Ơ kìa, ai vừa nhặt mất rương báu vậy?",
 "Mình nghĩ nên đổi chiến thuật ở hiệp sau.", "Xin lỗi, mình gõ nhầm, ý là ngày mười lăm.",
 "Bẫy ở bờ suối, cẩn thận kẻo ngã.", "Lũ quỷ ở đây mạnh hơn mình tưởng.",
 "Cưỡi ngựa nhanh lên, kẻo lỡ chuyến.", "Thủy thủ đoàn đã sẵn sàng rời cảng.",
 "Tạm biệt, chúc ngủ ngon và mơ đẹp!", "Ừm, vậy hẹn mười giờ sáng mai nhé.",
]
FONTS = {"arial": "/usr/share/fonts/msttcore/arial.ttf", "verdana_bold": "/usr/share/fonts/msttcore/verdanab.ttf",
         "liberation": "/usr/share/fonts/liberation-sans/LiberationSans-Regular.ttf"}
if os.name == "nt":  # chạy trên Windows
    FONTS = {"arial": r"C:\Windows\Fonts\arial.ttf", "verdana_bold": r"C:\Windows\Fonts\verdanab.ttf",
             "liberation": r"C:\Windows\Fonts\segoeui.ttf"}

def nfc(s): return ud.normalize("NFC", s)
def strip_diacritics(s):
    s = ud.normalize("NFD", s.replace("đ", "d").replace("Đ", "D"))
    return "".join(c for c in s if not ud.combining(c))
def norm_space(s): return " ".join(s.split())
def lev(a, b):
    if a == b: return 0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]

def noisy_bg(w, h, rng):
    low = rng.integers(0, 256, (4, 8, 3)).astype(np.uint8)
    bg = cv2.resize(low, (w, h), interpolation=cv2.INTER_CUBIC).astype(np.float32)
    bg += rng.normal(0, 18, (h, w, 3))
    for _ in range(6):  # vệt sáng / đường nét động
        p1 = (int(rng.integers(0, w)), int(rng.integers(0, h))); p2 = (int(rng.integers(0, w)), int(rng.integers(0, h)))
        cv2.line(bg, p1, p2, tuple(int(x) for x in rng.integers(80, 256, 3)), int(rng.integers(1, 4)))
    bg = np.clip(bg, 0, 255)
    bg = bg * 0.65  # lớp phủ tối bán trong suốt sau khung chat game
    return Image.fromarray(bg.astype(np.uint8)[:, :, ::-1])

STYLES = {
    # tên: (font, cỡ, màu chữ RGB, nền, viền)
    "chatapp_dark_15px": ("arial", 15, (219, 222, 225), "dark", 0),
    "game_gold_14px_outline": ("verdana_bold", 14, (255, 210, 80), "noisy", 1),
    "game_white_12px": ("liberation", 12, (245, 245, 245), "noisy", 0),
}

def render(text, style, rng):
    fname, size, fg, bgk, stroke = STYLES[style]
    font = ImageFont.truetype(FONTS[fname], size)
    l, t, r, b = font.getbbox(text, stroke_width=stroke)
    w, h = r - l + 24, b - t + 32
    img = Image.new("RGB", (w, h), (49, 51, 56)) if bgk == "dark" else noisy_bg(w, h, rng)
    d = ImageDraw.Draw(img)
    if bgk == "noisy" and not stroke:
        d.text((12 - l + 1, 16 - t + 1), text, font=font, fill=(0, 0, 0))  # bóng đổ
    d.text((12 - l, 16 - t), text, font=font, fill=fg, stroke_width=stroke, stroke_fill=(0, 0, 0))
    return img

def preprocess(img_rgb, mode, style):
    a = cv2.cvtColor(np.array(img_rgb), cv2.COLOR_RGB2BGR)
    if mode == "raw": return a
    if mode == "x2": return cv2.resize(a, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    if mode == "otsu_x2":
        g = cv2.cvtColor(a, cv2.COLOR_BGR2GRAY)
        _, bw = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        if bw.mean() < 127: bw = 255 - bw  # chữ đen trên nền trắng
        return cv2.cvtColor(cv2.resize(bw, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC), cv2.COLOR_GRAY2BGR)
    if mode == "hsv_mask_x2":  # đúng ngưỡng hsv_them_color trong config.example.json (h 20-40, s>=100, v>=150)
        hsv = cv2.cvtColor(a, cv2.COLOR_BGR2HSV)
        m = cv2.inRange(hsv, (20, 100, 150), (40, 255, 255))
        bw = 255 - m
        return cv2.cvtColor(cv2.resize(bw, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC), cv2.COLOR_GRAY2BGR)
    raise ValueError(mode)

def build_engines(which):
    from rapidocr import RapidOCR, OCRVersion, ModelType, LangRec
    eng = {}
    # Lưu ý: rapidocr 3.10.0 route lang "vi" -> PP-OCRv6 small (cùng model/dict với mặc định)
    if "v6" in which: eng["PP-OCRv6 small (mặc định, = lang vi)"] = RapidOCR(params={"Rec.lang_type": "vi"})
    if "v6medium" in which: eng["PP-OCRv6 medium"] = RapidOCR(params={"Rec.lang_type": "vi", "Rec.model_type": ModelType.MEDIUM})
    if "v5latin" in which: eng["PP-OCRv5 latin mobile"] = RapidOCR(params={"Rec.lang_type": LangRec.LATIN, "Rec.ocr_version": OCRVersion.PPOCRV5, "Rec.model_type": ModelType.MOBILE})
    if "vietocr" in which: eng["VietOCR vgg_seq2seq"] = VietOCREngine("vgg_seq2seq")
    if "vietocr_tf" in which: eng["VietOCR vgg_transformer"] = VietOCREngine("vgg_transformer")
    return eng

class VietOCREngine:
    """Nhận dạng bằng VietOCR trên các box do detector PP-OCRv6 tìm ra (VietOCR chỉ là recognizer)."""
    def __init__(self, name="vgg_seq2seq"):
        from vietocr.tool.predictor import Predictor
        from vietocr.tool.config import Cfg
        cfg = Cfg.load_config_from_name(name); cfg["device"] = "cpu"
        if os.environ.get("VIETOCR_WEIGHTS"): cfg["weights"] = os.environ["VIETOCR_WEIGHTS"]
        self.rec = Predictor(cfg)
    def __call__(self, arr):
        res = self.det(arr)
        class R: pass
        out = R(); out.boxes, out.txts = None, None
        if res is None or res.boxes is None: return out
        txts, boxes = [], []
        for b in res.boxes:
            b = np.array(b); x0, y0 = np.maximum(b.min(0).astype(int) - 2, 0); x1, y1 = b.max(0).astype(int) + 2
            crop = arr[y0:y1, x0:x1]
            if crop.size == 0: continue
            txts.append(self.rec.predict(Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)))); boxes.append(b.tolist())
        out.boxes, out.txts = boxes, txts
        return out

def run_engine(engine, arr):
    """Nhận dạng 1 dòng đã crop sẵn (rec-only) để đo đúng chất lượng recognizer + từ điển.
    (Detector PP-OCRv6 mặc định limit_type=min/736 sẽ phóng ảnh dòng 40px lên ~736px -> rất chậm trên CPU.)"""
    t0 = time.perf_counter()
    if engine.__class__.__name__ == "VietOCREngine":
        txt = engine.rec.predict(Image.fromarray(cv2.cvtColor(arr, cv2.COLOR_BGR2RGB)))
    else:
        res = engine(arr, use_det=False, use_cls=False, use_rec=True)
        txts = getattr(res, "txts", None) or ()
        txt = " ".join(t for t in txts if t)
    dt = (time.perf_counter() - t0) * 1000
    return norm_space(txt), dt

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", help="thư mục ảnh thật + labels.tsv")
    ap.add_argument("--engines", default="v6,v6medium,v5latin")
    ap.add_argument("--out", default="results")
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
    rng = np.random.default_rng(a.seed); random.seed(a.seed)
    engines = build_engines(a.engines.split(","))
    samples = []  # (style, preprocess, gt, image_array)
    if a.dataset:
        for fn, gt in csv.reader(open(os.path.join(a.dataset, "labels.tsv"), encoding="utf-8"), delimiter="\t"):
            img = Image.open(os.path.join(a.dataset, fn)).convert("RGB")
            for pm in ("raw", "x2"): samples.append(("dataset", pm, nfc(gt), preprocess(img, pm, "dataset")))
    else:
        for style in STYLES:
            for i, gt in enumerate(LINES):
                img = render(gt, style, rng)
                if i < 3: img.save(os.path.join(a.out, f"sample_{style}_{i}.png"))
                pms = ["raw", "x2", "otsu_x2"] + (["hsv_mask_x2"] if "gold" in style else [])
                for pm in pms: samples.append((style, pm, nfc(gt), preprocess(img, pm, style)))
    rows = []
    for ename, eng in engines.items():
        for style, pm, gt, arr in samples:
            pred, dt = run_engine(eng, arr); pred = nfc(pred)
            rows.append({"engine": ename, "style": style, "pre": pm, "gt": gt, "pred": pred, "ms": dt,
                         "cer": lev(pred, gt) / max(1, len(gt)),
                         "cer_nodiac": lev(strip_diacritics(pred).lower(), strip_diacritics(gt).lower()) / max(1, len(gt)),
                         "exact": pred == gt})
        print("done", ename, len(rows), file=sys.stderr, flush=True)
    with open(os.path.join(a.out, "predictions.tsv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), delimiter="\t"); w.writeheader(); w.writerows(rows)
    agg = {}
    for r in rows: agg.setdefault((r["engine"], r["style"], r["pre"]), []).append(r)
    out = ["| Engine | Kiểu ảnh | Tiền xử lý | CER có dấu | CER bỏ dấu | Dòng đúng 100% | ms/dòng (median) |", "|---|---|---|---|---|---|---|"]
    for (e, s, p), rs in sorted(agg.items()):
        out.append(f"| {e} | {s} | {p} | {statistics.mean(x['cer'] for x in rs):.1%} | {statistics.mean(x['cer_nodiac'] for x in rs):.1%} | "
                   f"{sum(x['exact'] for x in rs)}/{len(rs)} | {statistics.median(x['ms'] for x in rs):.0f} |")
    md = "\n".join(out); open(os.path.join(a.out, "summary.md"), "w", encoding="utf-8").write(md + "\n"); print(md)

if __name__ == "__main__":
    main()
