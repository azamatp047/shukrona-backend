#!/usr/bin/env python3
"""
Barcha botlarni bir vaqtda ishga tushirish uchun script
"""
import subprocess
import sys
import os
from pathlib import Path

def run_bot(bot_file):
    """Botni alohida jarayonda ishga tushirish"""
    print(f"🚀 {bot_file} ishga tushmoqda...")
    return subprocess.Popen([sys.executable, bot_file])

def main():
    """Barcha botlarni ishga tushirish"""
    print("=" * 50)
    print("🤖 Shukrona Delivery Bot System")
    print("=" * 50)
    
    # Botlar fayllari
    bots = [
        "bot_user.py",
        "bot_admin.py",
        "bot_courier.py"
    ]
    
    # Har bir bot faylini tekshirish
    for bot in bots:
        if not Path(bot).exists():
            print(f"❌ Xatolik: {bot} fayli topilmadi!")
            return
    
    print("\n📋 Botlarni ishga tushirish...\n")
    
    # Botlarni ishga tushirish
    processes = []
    for bot in bots:
        try:
            process = run_bot(bot)
            processes.append(process)
        except Exception as e:
            print(f"❌ {bot} ishga tushmadi: {e}")
    
    if not processes:
        print("\n❌ Hech qanday bot ishga tushmadi!")
        return
    
    print(f"\n✅ {len(processes)} ta bot muvaffaqiyatli ishga tushdi!")
    print("\n💡 To'xtatish uchun Ctrl+C bosing\n")
    
    try:
        # Botlar ishlayotgan paytda kutish
        for process in processes:
            process.wait()
    except KeyboardInterrupt:
        print("\n\n🛑 Botlar to'xtatilmoqda...")
        for process in processes:
            process.terminate()
        print("✅ Barcha botlar to'xtatildi.")

if __name__ == "__main__":
    main()