# API Spec

## 1.1. ESG 지수

## 1.2. Description

ESG 지수 정보를 제공 ('20년01월02일 데이터부터 제공)

Server endpoint url : https://data-dbg.krx.co.kr/svc/apis/esg/esg_index_info

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
| IDX_NM | string | 지수명 |
| CLSPRC_IDX | string | 현재가 |
| PRV_DD_CMPR | string | 전일비 |
| UPDN_RATE | string | 등락률 |
| TRD_ISU_CNT | string | 구성종목수 |
| ACC_TRDVOL | string | 거래량(천주) |
| ACC_TRDVAL | string | 거래대금(백만원) |

## 1.5. request Sample

```json
{"basDd":"__"}
```

## 1.6. response Sample

```json
{"OutBlock_1":[{"BAS_DD":"__","IDX_NM":"__","CLSPRC_IDX":"__","PRV_DD_CMPR":"__","UPDN_RATE":"__","TRD_ISU_CNT":"__","ACC_TRDVOL":"__","ACC_TRDVAL":"__"},{"BAS_DD":"__","IDX_NM":"__","CLSPRC_IDX":"__","PRV_DD_CMPR":"__","UPDN_RATE":"__","TRD_ISU_CNT":"__","ACC_TRDVOL":"__","ACC_TRDVAL":"__"}]}
```
