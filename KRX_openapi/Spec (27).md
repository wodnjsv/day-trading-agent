# API Spec

## 1.1. ESG 증권상품

## 1.2. Description

ESG 증권상품 정보를 제공 ('20년01월02일 데이터부터 제공)

Server endpoint url : https://data-dbg.krx.co.kr/svc/apis/esg/esg_etp_info

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
| ISU_ABBRV | string | 종목명 |
| TDD_CLSPRC | string | 현재가 |
| CMPPREVDD_PRC | string | 전일비 |
| FLUC_RT | string | 등락률 |
| LIST_SHRS | string | 상장좌수 |
| ACC_TRDVOL | string | 거래량(좌) |
| ACC_TRDVAL | string | 거래대금(원) |

## 1.5. request Sample

```json
{"basDd":"__"}
```

## 1.6. response Sample

```json
{"OutBlock_1":[{"BAS_DD":"__","ISU_ABBRV":"__","TDD_CLSPRC":"__","CMPPREVDD_PRC":"__","FLUC_RT":"__","LIST_SHRS":"__","ACC_TRDVOL":"__","ACC_TRDVAL":"__"},{"BAS_DD":"__","ISU_ABBRV":"__","TDD_CLSPRC":"__","CMPPREVDD_PRC":"__","FLUC_RT":"__","LIST_SHRS":"__","ACC_TRDVOL":"__","ACC_TRDVAL":"__"}]}
```
