# API Spec

## 1.1. 석유시장 일별매매정보

## 1.2. Description

KRX 석유시장의 매매정보 제공 ('12년03월30일 데이터부터 제공)

Server endpoint url : https://data-dbg.krx.co.kr/svc/apis/gen/oil_bydd_trd

## 1.3. request

### 1.3.1. InBlock_1

| Name | Type | Description |
| --- | --- | --- |
| basDd | string | 기준일자 |

## 1.4. response

### 1.4.1. OutBlock_1

| Name | Type | Description |
| --- | --- | --- |
| BAS_DD | string | 기준일자 |
| OIL_NM | string | 유종구분 |
| WT_AVG_PRC | string | 가중평균가격_경쟁 |
| WT_DIS_AVG_PRC | string | 가중평균가격_협의 |
| ACC_TRDVOL | string | 거래량 |
| ACC_TRDVAL | string | 거래대금 |

## 1.5. request Sample

```json
{"basDd":"__"}
```

## 1.6. response Sample

```json
{"OutBlock_1":[{"BAS_DD":"__","OIL_NM":"__","WT_AVG_PRC":"__","WT_DIS_AVG_PRC":"__","ACC_TRDVOL":"__","ACC_TRDVAL":"__"},{"BAS_DD":"__","OIL_NM":"__","WT_AVG_PRC":"__","WT_DIS_AVG_PRC":"__","ACC_TRDVOL":"__","ACC_TRDVAL":"__"}]}
```
