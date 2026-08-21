#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
========================================================================
 pf_collector.py — BỘ THU LOG pfSense (UDP syslog) -> FILE
========================================================================

VAI TRÒ (CHỈ thu thập & lưu trữ, KHÔNG phân tích, KHÔNG phân loại):
  1. NGHE syslog UDP từ pfSense (mặc định port 514).
  2. GHI từng dòng vào 1 file log DUY NHẤT, kèm TIMESTAMP THU NHẬN
     (ISO8601 UTC) ở đầu dòng, phân cách bằng TAB.
  3. Rotate khi file active đạt 5MB.

*** THAY ĐỔI SO VỚI BẢN TRƯỚC ***
  Bản trước collector tự nhận diện dòng nào là DHCP (is_dhcp_line) rồi
  tách ghi ra 2 file riêng (pfsense.log / dhcp.log) để 2 workflow n8n
  khác nhau đọc. Điều này SAI VỀ KIẾN TRÚC: collector chỉ nên làm nhiệm
  vụ "ống dẫn" (thu + ghi), việc PHÂN LOẠI log (PORT_SCAN / BRUTE_FORCE
  / DHCP...) là trách nhiệm của lớp phân tích (WF-ANALYZER trong n8n),
  không phải của lớp thu thập.

  Vì vậy bản này:
    - GHI TẤT CẢ các dòng log (filterlog, sshd, system, dhcpd, ipsec,
      openvpn...) vào CHUNG 1 file active: pfsense.log (rotate ra
      pfsense_<timestamp>.log).
    - WF-ANALYZER (n8n) sẽ đọc file này, tự phân loại dòng nào là
      PORT_SCAN / BRUTE_FORCE / DHCP..., rồi gọi (execute sub-workflow)
      tới WF-BLOCK-SCAN / WF-BLOCK-BRUTE / WF-DHCP-WATCH tương ứng.
    - Đã LOẠI BỎ hoàn toàn phần forward log sang n8n qua webhook
      (forward_to_n8n / N8N_WEBHOOK / FORWARD_TO_N8N) vì các workflow
      giờ đọc trực tiếp từ file log, không cần nhận qua webhook nữa.
      Việc bỏ webhook cũng giúp vòng lặp nhận UDP không phụ thuộc vào
      n8n có đang chạy/phản hồi kịp hay không.
========================================================================
"""

import os
import socket
from datetime import datetime, timezone


# ╔══════════════════════════════════════════════════════════════════╗
# ║ PHẦN 1 — CẤU HÌNH                                                 ║
# ╚══════════════════════════════════════════════════════════════════╝

LISTEN_IP   = "0.0.0.0"        # nghe trên MỌI card mạng của máy chạy collector
LISTEN_PORT = 514              # khớp port pfSense gửi syslog tới

PFSENSE_IP  = "192.168.10.1"
ONLY_ACCEPT_FROM_PFSENSE = False   # True = chỉ nhận gói từ pfSense (nên bật ở production)

LOG_DIR = r"C:\Users\Administrator\.n8n-files\pflogs"   # thư mục chứa file log

# --- 1 luồng log active duy nhất (mọi loại log đều ghi vào đây) ---
ACTIVE_LOG_NAME = "pfsense.log"   # file active -> WF-ANALYZER đọc & tự phân loại
LOG_PREFIX      = "pfsense"       # rotate -> pfsense_<timestamp>.log

ROTATE_MAX_BYTES = 5 * 1024 * 1024   # 5 MB -> rotate sang file mới có timestamp


# ╔══════════════════════════════════════════════════════════════════╗
# ║ PHẦN 2 — GHI FILE + ROTATE                                        ║
# ╚══════════════════════════════════════════════════════════════════╝

def _rotate_if_needed():
    """Nếu file active đã >= 5MB -> đổi tên thành <prefix>_<timestamp>.log.
    Lần ghi kế tiếp tự tạo file active mới (trống) vì open(...,'a') tự tạo.

    Tên có timestamp (kèm microsecond) để: sort tên = sort thời gian,
    không trùng dù rotate liên tiếp trong 1 giây, và phân biệt rõ file
    'đã đóng' (pfsense_*.log) với file 'đang active' (pfsense.log)."""
    path = os.path.join(LOG_DIR, ACTIVE_LOG_NAME)
    if not os.path.exists(path):
        return
    if os.path.getsize(path) < ROTATE_MAX_BYTES:
        return

    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    new_path = os.path.join(LOG_DIR, f"{LOG_PREFIX}_{ts}.log")
    os.rename(path, new_path)   # os.rename ATOMIC trên cùng filesystem -> an toàn
    print(f"[collector] rotate: {ACTIVE_LOG_NAME} "
          f"(>= {ROTATE_MAX_BYTES/1024/1024:.0f}MB) -> {os.path.basename(new_path)}")


def write_line(raw: str):
    """Ghi 1 dòng vào file active, kèm timestamp thu nhận (ISO8601 UTC)
    ở đầu dòng, phân cách bằng TAB. Kiểm tra rotate TRƯỚC khi ghi để
    không dòng nào lọt vào file đã vượt 5MB. KHÔNG phân loại nội dung
    dòng log — mọi phân loại (DHCP/PORT_SCAN/BRUTE_FORCE...) thuộc về
    WF-ANALYZER phía n8n."""
    _rotate_if_needed()
    ts = datetime.now(timezone.utc).isoformat()
    line = f"{ts}\t{raw}\n"
    with open(os.path.join(LOG_DIR, ACTIVE_LOG_NAME), "a", encoding="utf-8") as f:
        f.write(line)


# ╔══════════════════════════════════════════════════════════════════╗
# ║ PHẦN 3 — VÒNG LẶP CHÍNH: NHẬN SYSLOG TỪ pfSense                   ║
# ╚══════════════════════════════════════════════════════════════════╝

def main():
    os.makedirs(LOG_DIR, exist_ok=True)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((LISTEN_IP, LISTEN_PORT))
    print(f"[collector] nghe syslog UDP {LISTEN_IP}:{LISTEN_PORT}")
    print(f"[collector] {ACTIVE_LOG_NAME} <- TẤT CẢ log (WF-ANALYZER tự phân loại)")
    print(f"[collector] thu muc: {LOG_DIR}  (rotate {ROTATE_MAX_BYTES/1024/1024:.0f}MB)")

    while True:
        data, addr = sock.recvfrom(8192)
        sender_ip = addr[0]

        if ONLY_ACCEPT_FROM_PFSENSE and sender_ip != PFSENSE_IP:
            continue

        raw = data.decode("utf-8", errors="replace").strip()
        if not raw:
            continue

        print(f"[DEBUG] Nhan tu {sender_ip}: {raw[:120]}") 
        write_line(raw)


if __name__ == "__main__":
    main()
