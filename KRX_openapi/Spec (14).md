# API Spec

## 1.1. ELW 일별매매정보

## 1.2. Description

ELW(주식위런트증권)의 매매정보 제공 ('10년01월04일 데이터부터 제공)

Server endpoint url : https://data-dbg.krx.co.kr/svc/apis/etp/elw_bydd_trd

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
| ISU_CD | string | 종목코드 |
| ISU_NM | string | 종목명 |
| TDD_CLSPRC | string | 종가 |
| CMPPREVDD_PRC | string | 대비 |
| TDD_OPNPRC | string | 시가 |
| TDD_HGPRC | string | 고가 |
| TDD_LWPRC | string | 저가 |
| ACC_TRDVOL | string | 거래량 |
| ACC_TRDVAL | string | 거래대금 |
| MKTCAP | string | 시가총액 |
| LIST_SHRS | string | 상장증권수 |
| ULY_NM | string | 기초자산_자산명 |
| ULY_PRC | string | 기초자산_종가 |
| CMPPREVDD_PRC_ULY | string | 기초자산_대비 |
| FLUC_RT_ULY | string | 기초자산_등락률 |

## 1.5. request Sample

```json
{"basDd":"__"}
```

## 1.6. response Sample

```json
{"OutBlock_1":[{"BAS_DD":"__","ISU_CD":"__","ISU_NM":"__","TDD_CLSPRC":"-","CMPPREVDD_PRC":"-","TDD_OPNPRC":"-","TDD_HGPRC":"-","TDD_LWPRC":"-","ACC_TRDVOL":"-","ACC_TRDVAL":"-","MKTCAP":"-","LIST_SHRS":"-","ULY_NM":"-","ULY_PRC":"-","CMPPREVDD_PRC_ULY":"-","FLUC_RT_ULY":"-"},{"BAS_DD":"__","ISU_CD":"__","ISU_NM":"__","TDD_CLSPRC":"-","CMPPREVDD_PRC":"-","TDD_OPNPRC":"-","TDD_HGPRC":"-","TDD_LWPRC":"-","ACC_TRDVOL":"-","ACC_TRDVAL":"-","MKTCAP":"-","LIST_SHRS":"-","ULY_NM":"-","ULY_PRC":"-","CMPPREVDD_PRC_ULY":"-","FLUC_RT_ULY":"-"}]}
```
