# API Spec

## 1.1. KOSPI 시리즈 일별시세정보

## 1.2. Description

KOSPI 시리즈 지수의 시세정보 제공 ('10년01월04일 데이터부터 제공)

Server endpoint url : https://data-dbg.krx.co.kr/svc/apis/idx/kospi_dd_trd

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
| IDX_CLSS | string | 계열구분 |
| IDX_NM | string | 지수명 |
| CLSPRC_IDX | string | 종가 |
| CMPPREVDD_IDX | string | 대비 |
| FLUC_RT | string | 등락률 |
| OPNPRC_IDX | string | 시가 |
| HGPRC_IDX | string | 고가 |
| LWPRC_IDX | string | 저가 |
| ACC_TRDVOL | string | 거래량 |
| ACC_TRDVAL | string | 거래대금 |
| MKTCAP | string | 상장시가총액 |

## 1.5. request Sample

```json
{"basDd":"__"}
```

## 1.6. response Sample

```json
{"OutBlock_1":[{"BAS_DD":"__","IDX_CLSS":"__","IDX_NM":"__","CLSPRC_IDX":"-","CMPPREVDD_IDX":"-","FLUC_RT":"-","OPNPRC_IDX":"-","HGPRC_IDX":"-","LWPRC_IDX":"-","ACC_TRDVOL":"-","ACC_TRDVAL":"-","MKTCAP":"-"},{"BAS_DD":"__","IDX_CLSS":"__","IDX_NM":"__","CLSPRC_IDX":"-","CMPPREVDD_IDX":"-","FLUC_RT":"-","OPNPRC_IDX":"-","HGPRC_IDX":"-","LWPRC_IDX":"-","ACC_TRDVOL":"-","ACC_TRDVAL":"-","MKTCAP":"-"}]}
```
