# Taipei Blue Vote Trend

台北市 2000–2024 年總統選舉藍綠基本盤、其他候選人票與選票波動趨勢：可重現資料、分析程式、眷村所在地代理比較、青年補票估計與圖表。

![台北市泛藍總統票每屆增減](charts/taipei-blue-election-deltas.svg)

## 主要發現

| 指標 | 2000 | 2024 | 變化 |
|---|---:|---:|---:|
| 台北市泛藍票 | 979,102 | 587,258 | −391,844（−40.0%） |
| 台北市泛藍得票率 | 61.69% | 38.08% | −23.60 個百分點 |
| 固定深藍 cohort 泛藍票 | 391,330 | 218,485 | −172,845（−44.2%） |
| 固定深藍 cohort 泛藍率 | 69.66% | 43.72% | −25.94 個百分點 |
| 台北市泛綠票 | 597,465 | 587,899 | −9,566（−1.6%） |
| 台北市泛綠得票率 | 37.64% | 38.13% | +0.48 個百分點 |
| 固定深綠 cohort 泛綠票 | 142,725 | 122,604 | −20,121（−14.1%） |
| 固定深綠 cohort 泛綠率 | 49.25% | 45.54% | −3.71 個百分點 |

固定深藍 cohort 定義為：2000 年至少 100 張有效票、泛藍率至少 65%，且 2000–2024 七屆皆能以相同「行政區＋里名」配對的里，共 146 里。

固定深綠 cohort 以同樣方式定義，但門檻為 2000 年泛綠率至少 45%，共 86 里。

變化並非固定速度下降，而是「高檔震盪後階梯式下移」：2016 年是最大斷層（−12.41 個百分點、−269,870 票），2024 年是第二次大幅下移（−8.26 個百分點、−169,341 票）。2020 年票數增加 56,304 票，但占比仍下降 1.69 個百分點，顯示票數與相對支持度必須分開看。

## 藍綠及其他候選人口徑

| 年份 | 泛藍 | 泛綠 | 其他候選人 |
|---|---|---|---|
| 2000 | 宋楚瑜、連戰 | 陳水扁 | 許信良、李敖 |
| 2004 | 連戰 | 陳水扁 | — |
| 2008 | 馬英九 | 謝長廷 | — |
| 2012 | 馬英九、宋楚瑜 | 蔡英文 | — |
| 2016 | 朱立倫、宋楚瑜 | 蔡英文 | — |
| 2020 | 韓國瑜、宋楚瑜 | 蔡英文 | — |
| 2024 | 侯友宜 | 賴清德 | 柯文哲 |

宋楚瑜依原分析口徑列入泛藍。「其他候選人」是選票的可觀察分類，不等於所有中間選民。

## 綠營基本盤與中間選票代理

![臺北市藍綠與選票波動](charts/taipei-bloc-and-volatility.svg)

泛綠全市票在 2000–2024 只淨減 9,566 票，得票率反而增加 0.48 個百分點，但中間並非穩定成長：2020 年達 875,854 票、53.65%，2024 年一屆就減少 287,955 票、15.53 個百分點。固定 86 個深綠里在 2024 年也比 2000 年少 20,121 票、3.71 個百分點。

可直接觀察的其他候選人票為：2000 年 10,599 票（0.67%）、2004–2020 為 0、2024 年 366,854 票（23.79%）。其中的零主要代表當屆沒有本分類之外的候選人，不代表沒有中間選民。

三類選票波動指標所得的最低淨移動規模依序為：92,506、104,317、41,335、180,968、27,660 與 366,854 票等值。2024 年最高，為 23.79 個百分點。這是聚合淨變化的尺度，不是可識別的個人轉投人數。

## 青年補票估計

2024 年台北市 20–39 歲選舉人共 571,536 人。以約 71.5% 投票率及分齡民調支持區間估算，投給侯友宜約 55,168–65,384 票，中央值 61,297 票，相當於補回 2000–2024 泛藍票數流失的約 14.1%–16.7%。

這不是官方候選人×年齡交叉表，也不是個人層次的投票識別。秘密投票下，該數字只能是結合官方人口／投票率與調查支持率的區間估計。

## 里級年齡結構模型

![臺北市 2024 里級年齡結構模型](charts/village-age-model-2024.svg)

以戶政司 2023 年 12 月單一年齡人口與 2024 年總統票作行政區＋里別精確配對，456／456 里全數命中。有效票加權生態迴歸含行政區固定效果，加權 R² 為 0.509。

- 20–39 歲占比每高 10 個百分點，模型中侯友宜得票率約低 6.77 個百分點。
- 65 歲以上占比每高 10 個百分點，模型中得票率約高 5.26 個百分點。
- 每里的實際／預測得票率、預測票數、殘差與排名均在 `village_age_structure_2024.csv`。

這是同一時點的里級關聯模型，適合用來建立「單看年齡結構預期多藍」的基準線；不可解釋為個人因果，也不能單獨分解 2000–2024 的死亡、遷移或世代交替。

## 重建

需要 Python 3.11 以上，沒有第三方 runtime dependency。

```bash
PYTHONPATH=src python3 -m taipei_blue_vote --refresh
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

原始 CSV 下載至 gitignored 的 `data/raw/`。程式會重建：

- `data/derived/city_trend.csv`
- `data/derived/deep_blue_cohort.csv`
- `data/derived/deep_green_cohort.csv`
- `data/derived/bloc_deltas.csv`
- `data/derived/electoral_volatility.csv`
- `data/derived/election_deltas.csv`
- `data/derived/military_village_proxies.csv`
- `data/derived/young_replacement.csv`
- `data/derived/source_manifest.json`
- `data/derived/village_age_structure_2024.csv`
- `data/derived/age_model_2024.csv`
- `data/derived/age_source_manifest.json`
- `charts/taipei-blue-election-deltas.svg`
- `charts/taipei-blue-election-deltas.html`
- `charts/taipei-bloc-and-volatility.svg`
- `charts/taipei-bloc-and-volatility.html`
- `charts/village-age-model-2024.svg`
- `charts/village-age-model-2024.html`

## 資料來源

- [中選會選舉資料庫](https://db.cec.gov.tw/Visual)
- [TaiwanVotes CSV 下載與資料出處](https://taiwanvotes.tw/download/)：依中選會開放資料正規化；逐檔 URL、SHA-256、位元組數與列數見 source manifest。
- [中選會 2024 年選舉人年齡統計](https://web.cec.gov.tw/api/file/5f9a0a37-3df1-46a7-afcb-8fff36f1d800.pdf)
- [中選會年齡投票率研究](https://web.cec.gov.tw/api/file/c67a1f6c-544a-4065-ac96-ce53f183de5c.pdf)
- [TVBS 2023-12-22 分齡民調](https://cc.tvbs.com.tw/portal/file/poll_center/2023/20231222/adc5c803a4f2bbc2193a44e2b74f7492.pdf)
- [聯合報 2023-11-28 分齡民調](https://paper.udn.com/udnpaper/PID0001/390092/web/)
- [戶政司：村里戶數、單一年齡人口](https://data.gov.tw/dataset/77132)：本專案使用 2023 年 12 月 `ODRP014` API；快照 URL、SHA-256 與位元組數見 age source manifest。

完整方法、眷村代理里結果與限制見 [`report/findings.md`](report/findings.md)。

## 重要限制

- 泛藍是本專案的透明分類，不是中選會官方分類。
- 泛綠與其他候選人也是本專案的分類；其他票不等於中間選民人數。
- 選票波動是三類聚合得票率的最低淨移動尺度，無法看到互相抵銷的個人轉投。
- 里級彙總資料不能識別個人投票，也不能單獨區分死亡、遷移、都市更新、投票率與政黨轉向。
- 年齡模型是使用 2024 同屆選舉估計的描述基準，不是樣本外預測或因果識別。
- 眷村所在地代理里反映的是地理範圍，不等於眷村後代人口。
- 精確里名配對會排除改名、分里或合併的里，換取較可解釋的固定 cohort。

## License

程式碼採 MIT License。資料仍依各原始提供者的授權與註明方式使用。
