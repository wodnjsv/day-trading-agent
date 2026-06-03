# API Spec

## 1.1. 일반채권시장 일별매매정보

## 1.2. Description

일반채권시장에 상장되어있는 채권의 매매정보 제공 ('10년01월04일 데이터부터 제공)

Server endpoint url : https://data-dbg.krx.co.kr/svc/apis/bon/bnd_bydd_trd

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
| CLSPRC | string | 종가_가격 |
| CMPPREVDD_PRC | string | 종가_대비 |
| CLSPRC_YD | string | 종가_수익률 |
| OPNPRC | string | 시가_가격 |
| OPNPRC_YD | string | 시가_수익률 |
| HGPRC | string | 고가_가격 |
| HGPRC_YD | string | 고가_수익률 |
| LWPRC | string | 저가_가격 |
| LWPRC_YD | string | 저가_수익률 |
| ACC_TRDVOL | string | 거래량 |
| ACC_TRDVAL | string | 거래대금 |

## 1.5. request Sample

```json
{"basDd":"__"}
```

## 1.6. response Sample

```json
{"OutBlock_1":[{"BAS_DD":"__","MKT_NM":"__","ISU_CD":"__","ISU_NM":"__","CLSPRC":"__","CMPPREVDD_PRC":"__","CLSPRC_YD":"__","OPNPRC":"__","OPNPRC_YD":"__","HGPRC":"__","HGPRC_YD":"__","LWPRC":"__","LWPRC_YD":"__","ACC_TRDVOL":"__","ACC_TRDVAL":"__"},{"BAS_DD":"__","MKT_NM":"__","ISU_CD":"__","ISU_NM":"__","CLSPRC":"__","CMPPREVDD_PRC":"__","CLSPRC_YD":"__","OPNPRC":"__","OPNPRC_YD":"__","HGPRC":"__","HGPRC_YD":"__","LWPRC":"__","LWPRC_YD":"__","ACC_TRDVOL":"__","ACC_TRDVAL":"__"}]}
```
