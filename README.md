# iGotcha

**If you know, you know.**

---

## 🔧 Build Instructions

1. Install requirements:
   pip install pyautogui pyinstaller

2. From the folder containing `igotcha.py` and `igotcha.ico`, run:
   pyinstaller --noconsole --onefile --name "iGotcha" --icon="igotcha.ico" --add-data "igotcha.ico;." igotcha.py

3. Your standalone executable will be created in the `dist/` folder as:
   iGotcha.exe

---

## ▶️ Run Instructions

- Windows:  
  Double-click `iGotcha.exe` in the `dist/` folder.  

- Python (optional):  
  python igotcha.py

---

✨ That’s it. If you know, you know.
