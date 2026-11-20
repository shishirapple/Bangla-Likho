# বাংলা টাইপিং Linux-এ — IBus ইনপুট মেথড

Wayland-এ (KDE Plasma, GNOME) কোনো অ্যাপ্লিকেশনকে সিস্টেমজুড়ে কী পড়তে বা
টাইপ করতে দেওয়া হয় না। তাই Bangla Likho এখন একটি **IBus ইনপুট মেথড** দেয় —
এটাই Linux-এর সাপোর্টেড উপায়, এবং এটি **X11 ও Wayland দুটোতেই** কাজ করে,
প্রতিটি অ্যাপে (Qt, GTK, Electron, টার্মিনাল)।

## ইনস্টল (Kubuntu / KDE Plasma)

```bash
sudo apt install ibus python3-gi gir1.2-ibus-1.0      # একবার
cd Bangla-Likho
sudo bash ime/install-ime.sh --system                  # ইঞ্জিন বসায়
```

তারপর KDE-তে চালু করুন:

1. **System Settings → Keyboard → Input Method** (Plasma 6)
   অথবা **System Settings → Input Devices → Virtual Keyboard** (Plasma 5)
2. Input method framework হিসেবে **IBus** নির্বাচন করুন।
3. তালিকায় **Bangla Likho (Phonetic)** যোগ করে Apply করুন।
4. কিছু না হলে একবার লগ আউট করে আবার লগ ইন করুন, অথবা `im-config -n ibus`।

এরপর `Super+Space` (বা `Ctrl+Space`) চেপে ইংরেজি ↔ বাংলা বদলান।
যেকোনো অ্যাপে `kemon` লিখে Space চাপলে **কেমন** বসবে; সাজেশন তালিকা IBus
নিজেই দেখাবে (১–৯ চেপে বাছাই, ↑/↓ দিয়ে চলাচল)।

## GNOME / অন্য ডেস্কটপ

`Settings → Keyboard → Input Sources → + → Other → Bangla Likho (Phonetic)`

## কেন এটা আলাদা

| বিষয় | গ্লোবাল হুক (পুরোনো পথ) | IBus ইনপুট মেথড |
|---|---|---|
| Wayland | ✗ কাজ করে না | ✓ কাজ করে |
| KDE / GNOME | ✗ ক্র্যাশ ঝুঁকি | ✓ নেটিভ |
| টাইপিং | কী ধরে পুনরায় ইনজেক্ট | ✓ অ্যাপ নিজেই ইনপুট নেয় |
| সাজেশন | ভাসমান উইন্ডো | ✓ IBus-এর নিজের তালিকা |
| ক্লিপবোর্ড | পেস্ট করে বসাতে হয় | ✓ সরাসরি কমিট |

ইঞ্জিন বসানো থাকলে Bangla Likho ডেস্কটপ অ্যাপ আর গ্লোবাল হুক চালু করে না —
ডাবল কনভার্শন এড়াতে। জোর করে হুক চালাতে চাইলে: `bangla-likho --hook`।

## ইঞ্জিন সরানো

```bash
sudo bash ime/install-ime.sh --system --uninstall
```

## সমস্যা হলে

```bash
ibus list-engine | grep bangla          # তালিকায় আছে কি না
ibus engine bangla-likho                # সরাসরি চালু করে দেখা
ibus-daemon -drx                        # ডেমন চালু
```

ইঞ্জিনের নিজের পরীক্ষা:

```bash
/usr/local/bin/bangla-likho-ime --check   # ব্যাকগ্রাউন্ড ছাড়াই ক্যান্ডিডেট দেখায়
```

লগ দেখুন: `journalctl --user -u ibus -n 50` অথবা `ibus-daemon -drx -v`।
