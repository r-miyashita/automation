# upload.py


## 概要

💡S3へのファイルアップロードを自動化します


リストからアップロードパスとリソースを取得しファイルアップロードを完了させます

結果ファイルからClowdFront用に変換されたパブリックURLを取得することができます



<br><br>
## 機能
- <span style="background:palegreen">アップロード</span>　ファイルを任意のバケット配下へアップロードします
- <span style="background:palegreen">URL取得</span>　アップロードしたファイルのパブリックURLを取得します
- <span style="background:paleturquoise">ドメイン置換</span>　パブリックURL（S3）をCloudFront用のURLへ置換します
- <span style="background:paleturquoise">有効性チェック</span>　置換後のURLが有効であることをチェックします　



<br><br>
## 環境
```
📂automation/
│
├── 📂data/
│   └── 📂s3/
│       │
│       ├── 📄upload_file_list.txt #🔻input
│       ├── 📂files/ #🔻input
│       └── 📂logs/
│
├── 📂s3_operations/
│   │
│   ├── upload.py #✅ アップロード用の実行スクリプト
│   └── utils.py #共通処理
│
├── config.py
├── config.yml
└── requirements.txt
```


<br><br>
## 手順
1. `files/`　へアップロードファイルを格納してください
2. `file_list.txt`　にアップロード先を記述してください
3. `upload.py`　を実行してください
4. ＞＞＞　`result.txt`　が作成され、アップロード済みファイルのパブリックURLを確認することができます🎉🎉




<br><br>
---
## `📂files/`の準備

==🔴ディレクトリ直下==に必要なファイルを格納してください

（　ディレクト階層は設けないでください　）

```
📁files/
│
├── カタログ_***.pdf
├── メイン画像_***.png
├── サムネ_***.jpg
├── 試験結果_***.pdf
├── 価格表A_***.pdf
└── 価格表B_***.pdf
```



----
## `📄upload_file_list.txt`の準備

`アップロード先の階層+ファイル名`　をリストに記載してください



==🔴バケット名より先の階層==　がアップロードに必要な情報です
- ==🟢バケット名==/ ==🔴親_ディレクトリ/ 子_ディレクトリ/ 孫_ディレクトリ/ ファイル.pdf==



📍例）バケット：`test_bucket`　配下の`製品A`ディレクトリに　`カタログ_***.pdf`をアップロードする

- S3の階層: ==🟢test_bucket==/ ==🔴navi/info/product/製品A/カタログ_***.pdf==


```
📄upload_file_list.txt

navi/info/product/製品A/カタログ_***.pdf 👈このように書く！
navi/info/product/製品A/メイン画像_***.png
navi/info/product/製品A/サムネ_***.jpg
navi/info/product/製品B/試験結果_***.pdf
navi/info/document/価格表/価格表A_***.pdf
navi/info/document/価格表/価格表B_***.pdf
```

ちなみに、末尾のファイル名は `files/` 　からアップロードする際にファイルを特定するためのキーとなっています。



🚨⚡️　`中身違い、同名ファイル`　の取り扱いには注意してください！！

files/  は直下のみの参照とし、階層構造を持たない仕様です
ファイル名が重複するリソースは管理できません


次のようなケースでは　誤アップロード　のリスクがあります
```
📄upload_file_list

# 階層は違う。ただしファイル名は同じ。
navi/info/product/ 製品A /カタログ_aaa.pdf # ①
navi/info/product/ 製品B /カタログ_aaa.pdf # ②

-----------------------------------------

# 階層違いだが、それぞれ同じファイルをアップしたい ( ① == ② )　であれば問題ない ✅
# ファイル名は同じ。しかし中身が違う　( ① != ② )　であれば　同時にアップロードすることはできない ❌


```

 files/直下に配置できる　 `カタログ_aaa.pdf` 　は必ず1種のみなので、どちらかは誤ったファイルがアップされることになります。



こういったケースでは以下を参考に　誤アップロード　を回避してください💪🏻
- それぞれ一意なファイル名に変更
- 複数回に分けてファイルをアップロードする



---

#automation/s3_operations
