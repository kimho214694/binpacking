"""
두 장 사진으로 상자 3D 치수 측정

촬영 방법:
  1. 위에서 수직으로 촬영  : A4 용지를 상자 옆에 놓고 정수리 위에서 찍기 → 가로(W), 세로(L)
  2. 옆에서 수직으로 촬영  : A4 용지를 상자 옆에 세우고 정면에서 찍기  → 높이(H)

  공통 주의사항:
  - 배경은 어두운 바닥/책상 위에서 촬영 (흰 상자와 대비 필요)
  - A4 용지와 상자가 모두 화면 안에 들어와야 함
  - 카메라를 최대한 수직/수평으로 유지

사용법:
  python vision/box_detector.py --top 위사진.jpg --side 옆사진.jpg
"""

import argparse
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import cv2
import numpy as np

# A4 용지 실제 크기 (cm)
A4_SHORT = 21.0
A4_LONG  = 29.7
A4_RATIO = A4_LONG / A4_SHORT  # ≈ 1.414


# ── 이미지 처리 유틸 ──────────────────────────────────────────────────────────

def _preprocess(image):
    """그레이스케일 → 블러 → Canny 엣지 → 팽창"""
    gray  = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur  = cv2.GaussianBlur(gray, (7, 7), 0)
    edges = cv2.Canny(blur, 30, 100)
    kernel = np.ones((3, 3), np.uint8)
    edges  = cv2.dilate(edges, kernel, iterations=1)
    return edges


def _find_rectangles(image, min_area_ratio=0.01):
    """이미지에서 사각형 윤곽선을 모두 찾아 면적 내림차순으로 반환합니다."""
    h, w   = image.shape[:2]
    min_area = h * w * min_area_ratio

    edges = _preprocess(image)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    rects = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area:
            continue
        peri  = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.03 * peri, True)
        if len(approx) == 4:
            x, y, bw, bh = cv2.boundingRect(approx)
            aspect = max(bw, bh) / min(bw, bh)
            rects.append({"contour": approx,
                           "x": x, "y": y, "w": bw, "h": bh,
                           "area": area, "aspect": aspect})

    return sorted(rects, key=lambda r: r["area"], reverse=True)


def _identify_a4_and_box(rects):
    """
    사각형 목록에서 A4 용지와 상자를 식별합니다.
    상위 5개 후보 중 비율이 A4(1.414)에 가장 가까운 것 → A4 용지
    나머지 중 가장 큰 것 → 상자
    """
    if len(rects) < 2:
        return None, None

    candidates = rects[:5]
    a4_idx = min(range(len(candidates)),
                 key=lambda i: abs(candidates[i]["aspect"] - A4_RATIO))
    a4     = candidates[a4_idx]
    others = [r for i, r in enumerate(candidates) if i != a4_idx]
    box    = max(others, key=lambda r: r["area"]) if others else None

    return a4, box


def _calc_scale(a4_rect):
    """A4 용지의 픽셀 크기로 '픽셀당 cm' 비율을 계산합니다."""
    long_px  = max(a4_rect["w"], a4_rect["h"])
    short_px = min(a4_rect["w"], a4_rect["h"])
    return (A4_LONG / long_px + A4_SHORT / short_px) / 2


def _save_debug_image(img, a4, box, image_path, suffix):
    """감지 결과를 이미지에 그려 results/ 폴더에 저장합니다."""
    out = img.copy()

    # A4 — 파란색
    cv2.rectangle(out, (a4["x"], a4["y"]),
                  (a4["x"]+a4["w"], a4["y"]+a4["h"]), (255, 100, 0), 3)
    cv2.putText(out, "A4 (reference)", (a4["x"], a4["y"] - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 100, 0), 2)

    # 상자 — 초록색
    cv2.rectangle(out, (box["x"], box["y"]),
                  (box["x"]+box["w"], box["y"]+box["h"]), (0, 200, 0), 3)
    cv2.putText(out, "BOX", (box["x"], box["y"] - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 200, 0), 2)

    results_dir = os.path.join(os.path.dirname(__file__), "..", "results")
    os.makedirs(results_dir, exist_ok=True)
    base      = os.path.splitext(os.path.basename(image_path))[0]
    save_path = os.path.join(results_dir, f"{base}_{suffix}_measured.jpg")
    cv2.imwrite(save_path, out)
    print(f"  결과 이미지 저장: {save_path}")


# ── 측정 함수 ─────────────────────────────────────────────────────────────────

def measure_top_view(image_path):
    """
    위에서 찍은 사진으로 상자의 가로(W)와 세로(L)를 측정합니다.

    Returns: {"width": float, "length": float}  단위: cm
    """
    img = cv2.imread(image_path)
    if img is None:
        print(f"[오류] 이미지를 읽을 수 없습니다: {image_path}")
        return None

    rects    = _find_rectangles(img)
    a4, box  = _identify_a4_and_box(rects)

    if a4 is None or box is None:
        print("[오류] A4 용지 또는 상자를 감지하지 못했습니다.")
        print("  → 배경이 충분히 어두운지, A4와 상자가 모두 화면 안에 있는지 확인하세요.")
        return None

    scale = _calc_scale(a4)
    w_cm  = round(box["w"] * scale, 1)
    l_cm  = round(box["h"] * scale, 1)

    print(f"\n[위 사진 측정]")
    print(f"  A4 감지   : {a4['w']}×{a4['h']} px")
    print(f"  상자 감지 : {box['w']}×{box['h']} px  (scale: {scale:.4f} cm/px)")
    print(f"  → 가로(W): {w_cm} cm  /  세로(L): {l_cm} cm")

    _save_debug_image(img, a4, box, image_path, "top")
    return {"width": w_cm, "length": l_cm}


def measure_side_view(image_path):
    """
    옆에서 찍은 사진으로 상자의 높이(H)를 측정합니다.

    Returns: {"height": float}  단위: cm
    """
    img = cv2.imread(image_path)
    if img is None:
        print(f"[오류] 이미지를 읽을 수 없습니다: {image_path}")
        return None

    rects    = _find_rectangles(img)
    a4, box  = _identify_a4_and_box(rects)

    if a4 is None or box is None:
        print("[오류] A4 용지 또는 상자를 감지하지 못했습니다.")
        print("  → 배경이 충분히 어두운지, A4와 상자가 모두 화면 안에 있는지 확인하세요.")
        return None

    scale = _calc_scale(a4)
    h_cm  = round(box["h"] * scale, 1)

    print(f"\n[옆 사진 측정]")
    print(f"  A4 감지   : {a4['w']}×{a4['h']} px")
    print(f"  상자 감지 : {box['w']}×{box['h']} px  (scale: {scale:.4f} cm/px)")
    print(f"  → 높이(H): {h_cm} cm")

    _save_debug_image(img, a4, box, image_path, "side")
    return {"height": h_cm}


def measure_box(top_image_path, side_image_path):
    """
    위/옆 두 장 사진으로 상자의 W, L, H를 모두 측정합니다.

    Returns: {"width": float, "length": float, "height": float}  단위: cm
    """
    print("=" * 50)
    print("  3D 상자 치수 측정 (두 장 사진)")
    print("=" * 50)

    top  = measure_top_view(top_image_path)
    side = measure_side_view(side_image_path)

    if top is None or side is None:
        print("\n[실패] 측정에 실패했습니다. 사진을 다시 찍어주세요.")
        return None

    result = {
        "width":  top["width"],
        "length": top["length"],
        "height": side["height"],
    }

    print(f"\n{'='*50}")
    print(f"  최종 측정 결과")
    print(f"  가로(W) : {result['width']} cm")
    print(f"  세로(L) : {result['length']} cm")
    print(f"  높이(H) : {result['height']} cm")
    print(f"{'='*50}\n")

    return result


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="두 장 사진으로 상자 3D 치수 측정")
    parser.add_argument("--top",  required=True, help="위에서 찍은 사진 경로")
    parser.add_argument("--side", required=True, help="옆에서 찍은 사진 경로")
    args = parser.parse_args()

    measure_box(args.top, args.side)
