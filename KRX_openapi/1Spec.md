# API Spec

## 1.1. 신주인수권증서 일별매매정보

## 1.2. Description

유가증권/코스닥시장에 상장되어 있는 신주인수권증서의 매매정보 제공 ('10년02월12일 데이터부터 제공)

Server endpoint url : https://data-dbg.krx.co.kr/svc/apis/sto/sr_bydd_trd

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
| MKT_NM | string | 시장구분 |
| ISU_CD | string | 종목코드 |
| ISU_NM | string | 종목명 |
| TDD_CLSPRC | string | 종가 |
| CMPPREVDD_PRC | string | 대비 |
| FLUC_RT | string | 등락률 |
| TDD_OPNPRC | string | 시가 |
| TDD_HGPRC | string | 고가 |
| TDD_LWPRC | string | 저가 |
| ACC_TRDVOL | string | 거래량 |
| ACC_TRDVAL | string | 거래대금 |
| MKTCAP | string | 시가총액 |
| LIST_SHRS | string | 상장증서수 |
| ISU_PRC | string | 신주발행가 |
| DELIST_DD | string | 상장폐지일 |
| TARSTK_ISU_SRT_CD | string | 목적주권_종목코드 |
| TARSTK_ISU_NM | string | 목적주권_종목명 |
| TARSTK_ISU_PRSNT_PRC | string | 목적주권_종가 |

## 1.5. request Sample

```json
{"basDd":"__"}
```

## 1.6. response Sample

```json
{"OutBlock_1":[{"BAS_DD":"__","MKT_NM":"__","ISU_CD":"__","ISU_NM":"__","TDD_CLSPRC":"-","CMPPREVDD_PRC":"-","FLUC_RT":"-","TDD_OPNPRC":"-","TDD_HGPRC":"-","TDD_LWPRC":"-","ACC_TRDVOL":"-","ACC_TRDVAL":"-","MKTCAP":"-","LIST_SHRS":"__","ISU_PRC":"__","DELIST_DD":"__","TARSTK_ISU_SRT_CD":"__","TARSTK_ISU_NM":"__","TARSTK_ISU_PRSNT_PRC":"-"},{"BAS_DD":"__","MKT_NM":"__","ISU_CD":"__","ISU_NM":"__","TDD_CLSPRC":"-","CMPPREVDD_PRC":"-","FLUC_RT":"-","TDD_OPNPRC":"-","TDD_HGPRC":"-","TDD_LWPRC":"-","ACC_TRDVOL":"-","ACC_TRDVAL":"-","MKTCAP":"-","LIST_SHRS":"__","ISU_PRC":"__","DELIST_DD":"__","TARSTK_ISU_SRT_CD":"__","TARSTK_ISU_NM":"__","TARSTK_ISU_PRSNT_PRC":"-"}]}
```
