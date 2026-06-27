# -*- coding: utf-8 -*-
# Copyright (c) 2026 Tachibana Securities Co., Ltd. All rights reserved.

# 2021.07.08,   yo.
# 2023.4.18 reviced,   yo.
# 2025.07.27 reviced,   yo.
# 2026.06.21 reviced,   yo.
#
# 立花証券ｅ支店ＡＰＩ利用のサンプルコード
#
# 動作確認
# Python 3.13.5 / debian13
# API v4r9
#
# ------------------------------------------------------------------
#
# APIの基本設計について
# 
# 本APIは、プログラミング初心者や非ITエンジニアの方にも
# 利用しやすいよう、URLにJSON形式のパラメーターを付加して
# 送信する独自方式を採用しています。
# 
# 一般的なWeb APIとは異なる構成ですが、
# HTTPヘッダーやPOSTデータなどの知識を最小限に
# 抑えながら利用できることを重視しています。
# 
# このため、本APIは、URLとJSON文字列を組み立てて
# 送信するだけで利用でき、特別な知識を必要とせず、
# 各種スクリプト言語からも実装しやすいことを
# 優先した設計となっています。
#  
# ------------------------------------------------------------------
# 
# 固定IP指定の推奨
# 
# 秘密鍵、第2パスワードファイル、またはログインレスポンスファイルが
# 万が一流出した場合、第三者に不正ログインされるリスクがあります。
# 
# 安全のため、接続元を固定IPに限定する設定（IP制限）を
# 行っての利用を強く推奨いたします。
# 
# ------------------------------------------------------------------
# 
# 機能: 日足株価取得
#
# 必要な設定項目
# 銘柄コード:       S_ISSUE_CODE    （通常銘柄は4桁、優先株等は5桁。例、伊藤園'2593'、伊藤園優先株'25935'）
# 市場:             S_SIZYOU_C      （00:東証   現在(2021/07/01)、東証のみ可能。）
# 出力ファイル名:   FNAME_OUTPUT    （デフォルトは、'price_list_[銘柄コード].csv'）
#
#
# 利用方法: 
# 事前に「e_api_login_pubkey.py」を実行して、仮想URL等を取得しておいてください。
# 実行は「e_api_login_pubkey.py」と同じディレクトリで行ってください。
#
# ファイル構成：
# ~/e_api/                              ← API実行基盤（権限: 700 / 所有者のみアクセス可）
# ├── .auth/                        ← 鍵・暗号化データ格納（権限: 700）
# │   ├── file_pwd2.txt             ← 第2パスワード保存ファイル（手動作成。注文・訂正・取消以外は不要）
# │   └── file_login_response.txt   ← ログイン応答出力先（自動生成）
# ├── file_url_info.txt             ← API接続情報ファイル（手動作成）
# ├── e_api_login_pubkey.py
# │
# └── [本実行プログラム]
# 
# 
# ~/e_api/file_url_info.txtの内容例：
# {
#     "sUrl": "https://demo-kabuka.e-shiten.jp/e_api_v4r9/",
#     "sJsonOfmt": "5"
# }
#
#
#
#
# 参考資料（必ず最新の資料を参照してください。）--------------------------
#マニュアル
#「ｅ支店・ＡＰＩ、ブラウザからの利用方法」
# (api_web_access.xlsx)
# シート「マスタ・時価」
# ２－２．各Ｉ／Ｆ説明 
# （３）蓄積情報問合取得I/F
#
#
#
# == ご注意: ========================================
#   本番環境に接続した場合、実際に市場に注文が出ます。
#   市場で約定した場合取り消せません。
# ==================================================
#

import urllib3
import datetime
import json
import os
import urllib.parse
from zoneinfo import ZoneInfo

# =========================================================================
# --- 設定項目（定数定義） ---
# =========================================================================
# コマンド用パラメーター -------------------    
S_ISSUE_CODE = '1234'   # 10.銘柄コード。実際の銘柄コードを入れてください。
S_SIZYOU_C = '00'       # 11.市場。  00:東証   現在(2021/07/01)、東証のみ可能

FNAME_OUTPUT = 'price_list_' + S_ISSUE_CODE + '.csv'   # 書き込むファイル名。カレントディレクトリに上書きモードでファイルが作成される。

# --- 共通設定項目 ------------------------------------------------------------
FNAME_URL_INFO = "file_url_info.txt"                # API接続情報ファイル
FNAME_PASSWD2 = "./.auth/file_pwd2.txt"              # 第二パスワード保存ファイル
FNAME_LOGIN_RESPONSE = "./.auth/file_login_response.txt"  # ログイン応答保存先
FNAME_INFO_P_NO = "file_info_p_no.txt"              # p_no保存ファイル

# --- 通信堅牢化のための設定項目 ---
API_TIMEOUT_SECONDS = 15.0  # タイムアウト時間（秒）: 応答がない場合15秒で切り上げる
MAX_RETRY_COUNT = 3         # 最大リトライ回数: 通信エラー時に自動再試行する回数
RETRY_INTERVAL_SECONDS = 5  # リトライ間隔（秒）: 再試行する前に待機する時間
# =========================================================================

S_ISSUE_CODE = '9432'   # 10.銘柄コード。実際の銘柄コードを入れてください。
S_SIZYOU_C = '00'       # 11.市場。  00:東証   現在(2021/07/01)、東証のみ可能。



# --- 共通ユーティリティ関数 ----------------------------------------------

def func_p_sd_date():
    """
    機能: システム時刻を"p_sd_date"の書式の文字列で返す。
    返値: "p_sd_date"の書式の文字列。 API規定書式 "YYYY.MM.DD-hh:mm:ss.sss"
    引数1: なし
    備考: 
        日本標準時（Japan Standard Time、JST）を利用のこと。
    """
    dt_now = datetime.datetime.now(
        # 日本標準時（Japan Standard Time、JST）を利用
        ZoneInfo("Asia/Tokyo")
    )
    # 年.月.日-時:分:秒 の部分を作成
    str_date = dt_now.strftime("%Y.%m.%d-%H:%M:%S")
    
    # マイクロ秒（6桁ゼロ埋め）から先頭の3桁を切り出してミリ秒を作成
    str_micro = f"{dt_now.microsecond:06d}"
    str_ms = str_micro[0:3]
    
    # ドットで結合してAPI規定書式を完成
    return str_date + "." + str_ms


def func_replace_urlencode(str_input):
    """
    URLエンコードを行う。

    URLでは、スペースや「&」「+」「?」などの記号が
    特別な意味を持つため、そのまま送信できない場合がある。
    そのため、これらの文字を「%xx」形式へ変換する。

    例:
        "A B+C" → "A%20B%2BC"

    本サンプルでは Python標準ライブラリの
    urllib.parse.quote() を利用してURLエンコードを行う。

    他言語へ移植する場合も、自前で変換処理を作成するのではなく、
    各言語が提供する標準のURLエンコード関数を利用することを推奨する。

    主な対応例:
        Python      : urllib.parse.quote()
        Java        : java.net.URLEncoder.encode()
        C#          : Uri.EscapeDataString()
        JavaScript  : encodeURIComponent()
        Go          : url.QueryEscape()

    Parameters
    ----------
    str_input : str
        URLエンコード対象文字列

    Returns
    -------
    str
        URLエンコード後の文字列
    """
    return urllib.parse.quote(str_input, safe='')


def func_read_from_file(str_fname):
    """ファイルから文字情報を一括読み込み（BOMを排除）"""
    str_read = ''
    try:
        # utf-8-sig を指定してBOMを自動的に排除しファイルを開く
        with open(str_fname, 'r', encoding='utf-8-sig') as fin:
            while True:
                line = fin.readline()
                if not line:
                    break
                str_read = str_read + line
        return str_read
    except IOError as e:
        print(f"[エラー] ファイルを読み込めません: {str_fname}")
        raise e


def func_write_to_file(str_fname_output, str_data):
    """ファイルに書き込み、権限を所有者のみ(600)に制限"""
    try:
        # 出力先フォルダの存在を確認し、存在しない場合は自動作成
        str_dir = os.path.dirname(str_fname_output)
        if str_dir and not os.path.exists(str_dir):
            os.makedirs(str_dir, exist_ok=True)

        # データをファイルへ書き込み
        with open(str_fname_output, 'w', encoding='utf-8') as fout:
            fout.write(str_data)
        
        # パーミッションを600（所有者のみ読み書き可能）に制限
        os.chmod(str_fname_output, 0o600)
    except IOError as e:
        print(f"[エラー] ファイルに書き込めません: {str_fname_output}")
        raise e


def func_get_url_info(fname):
    """
    file_url_info.txt からAPI接続設定を取得

    機能: API接続情報をファイルから取得し辞書型で返す
    引数1: 接続先情報を保存したファイル名: fname_url_info

    サポートへの問い合わせは、sJsonOfmt:'5'でお願いします。
    """
    str_url_info = func_read_from_file(fname)
    # JSON形式の文字列を辞書型で取り出す
    return  json.loads(str_url_info)    


def func_get_login_response(str_fname):
    '''
    ログインレスポンスを取得
    '''
    str_login_response = func_read_from_file(str_fname)
    dic_login_response = json.loads(str_login_response)
    return dic_login_response
    

def func_get_p_no(fname):
    """ 
    機能: p_noをファイルから取得する
    引数1: p_noを保存したファイル名（fname_info_p_no = "e_api_info_p_no.txt"）
    """
    str_p_no_info = func_read_from_file(fname)
    # JSON形式の文字列を辞書型で取り出す
    json_p_no_info = json.loads(str_p_no_info)
    int_p_no = int(json_p_no_info.get('p_no'))
    return int_p_no


def func_save_p_no(str_fname_output, int_p_no):
    """p_noを保存するためのJSONファイルを生成"""
    p_no_dict = {"p_no": str(int_p_no)}
    json_data = json.dumps(p_no_dict, indent=4)
    func_write_to_file(str_fname_output, json_data)
    print(f'現在の "p_no" を保存しました。 p_no = {int_p_no} -> {str_fname_output}')


def func_make_url_request_from_dic(
                                    auth_flg,       # ログインFlag。    login:true   login以外:false
                                    url_target,     # 接続先URL
                                    work_dic_req    # API要求項目
):
    '''
    API問合せ用完全URL（クエリパラメータ付）を作成
    
    ------------------------------------------------------------------

    APIの基本設計について

    本APIは、プログラミング初心者や非ITエンジニアの方にも
    利用しやすいよう、URLにJSON形式のパラメーターを付加して
    送信する独自方式を採用しています。

    一般的なWeb APIとは異なる構成ですが、
    HTTPヘッダーやPOSTデータなどの知識を最小限に
    抑えながら利用できることを重視しています。

    このため、本APIは、URLとJSON文字列を組み立てて
    送信するだけで利用でき、特別な知識を必要とせず、
    各種スクリプト言語からも実装しやすいことを
    優先した設計となっています。
    
    ------------------------------------------------------------------
    JSONをHTTPボディではなくURLに付加して送信します。
    詳細はAPIマニュアル参照。
    備考：
        サポートへの問い合わせを考慮し、項目ごとの改行とタブを入れてあります。
    '''
    str_url = url_target
    if auth_flg:
        str_url = urllib.parse.urljoin(str_url, 'auth/')
    json_param = json.dumps(work_dic_req, indent=4, ensure_ascii=False)
    return f"{str_url}?{json_param}"


def func_api_req(str_request_method, str_url): 
    """
    APIリクエストの送信と、Shift-JIS応答のデコード（リトライ・タイムアウト対応版）
    """
    # HTTP通信ライブラリ urllib3 を利用します。
    #
    # requests ライブラリでも同様の処理は可能ですが、
    # 本サンプルでは APIサーバーへの接続処理が分かりやすいよう、
    # より基本的な urllib3 を利用しています。
    #
    # 他言語へ移植する場合も、
    # 「HTTPクライアント生成 → リクエスト送信 → レスポンス受信」
    # の流れを対応するライブラリへ置き換えてください。

    print('--- 送信電文 -------------------------------------------')
    print(str_url)

    # 接続および読み込みのタイムアウト時間を設定
    timeout_config = urllib3.Timeout(connect=API_TIMEOUT_SECONDS, read=API_TIMEOUT_SECONDS)
    http = urllib3.PoolManager()
    
    response_data = None
    status_code = None

    # 最大試行回数に達するまで通信をリトライ
    for attempt in range(1, MAX_RETRY_COUNT + 1):
        try:
            # 2回目以降の試行（再接続）の前に、指定されたインターバル時間待機
            if attempt > 1:
                print(f"[{attempt}/{MAX_RETRY_COUNT} 回目] 再接続を試みます...（{RETRY_INTERVAL_SECONDS}秒待機）")
                time.sleep(RETRY_INTERVAL_SECONDS)

            req = http.request(str_request_method, str_url, timeout=timeout_config)
            status_code = req.status
            response_data = req.data
            break  # 正常に通信できた場合はループを抜ける

        except (TimeoutError, MaxRetryError) as ce:
            print(f"\n[警告] 通信エラーが発生しました (試行: {attempt}/{MAX_RETRY_COUNT})")
            print(f"エラー詳細: {ce}")
            
            # 最大リトライ回数を超えて失敗した場合はConnectionErrorを発生
            if attempt == MAX_RETRY_COUNT:
                raise ConnectionError(
                    f"APIサーバーへの接続に規定回数失敗しました。サーバーがメンテナンス中か、停止している可能性があります。\n"
                    f"設定されたタイムアウト時間: {API_TIMEOUT_SECONDS}秒"
                )
        except Exception as ex:
            print(f"\n[警告] 予期せぬネットワーク例外が発生しました: {ex}")
            if attempt == MAX_RETRY_COUNT:
                raise ex

    print(f"HTTP Status: {status_code}")

    # 受信した電文をShift-JISからUTF-8へデコード（不正なバイトは無視）
    str_response = response_data.decode("shift-jis", errors="ignore")
    print('--- 受信電文 -------------------------------------------')
    print(str_response[:2000])
    print('--------------------------------------------------------')

    return str_response


def func_api_request_from_dic(
                                flg_login,          # ログインFlag。    login:true   login以外:false
                                destination_url,    # 接続先URL。
                                                    #   ログイン時は、FNAME_URL_INFOから取得する接続先。
                                                    #   それ以外はログインレスポンスで指定される仮想URL。
                                dic_req_item        # API要求項目
):
    '''
    APIへの問い合わせを実行する。
    '''
    # URL文字列の作成
    str_url = func_make_url_request_from_dic(
                                                flg_login,          # ログインFlag。    login:true   login以外:false
                                                destination_url,    # 接続先URL
                                                dic_req_item        # API要求項目
    )

    # APIへの問い合わせ。
    # リクエストメソッドの指定('GET'、'POST'どちらでも動作します。)
    str_api_response = func_api_req('POST', str_url)

    # apiの返り値（JSON形式の文字列）を辞書型で取り出す
    dic_api_response = json.loads(str_api_response)
    
    return dic_api_response

# --- 共通ユーティリティ関数 ----------------------------------------------




# 参考資料（必ず最新の資料を参照してください。）--------------------------
#マニュアル
#「ｅ支店・ＡＰＩ、ブラウザからの利用方法」
# (api_web_access.xlsx)
# シート「マスタ・時価」
# ２－２．各Ｉ／Ｆ説明 
# （３）蓄積情報問合取得I/F
#  を参照してください。


# 要求
# 1	sCLMID      CLMMfdsGetMarketPriceHistory
# 2	sIssueCode  対象の銘柄コード、１要求１銘柄指定。
# 3	sSizyouC    対象の市場コード（現在"00":東証のみ）、引数省略可能（デフォルト＝東証）。


# 応答
# No	項目	設定値								
# 1	sDate   日付（YYYYMMDD）								
# 2	pDOP	始値								
# 3	pDHP	高値								
# 4	pDLP	安値								
# 5	pDPP	終値								
# 6	pDV	出来高								
# 7	pDOPxK	株式分割換算係数で計算した該当値								
# 8	pDHPxK	株式分割換算係数で計算した該当値								
# 9	pDLPxK	株式分割換算係数で計算した該当値								
#10	pDPPxK	株式分割換算係数で計算した該当値								
#11	pDVxK	株式分割換算係数で計算した該当値						
#12	pSPUO	株式分割前単位	※株式分割日のみ設定
#13	pSPUC	株式分割後単位	※株式分割日のみ設定
#14	pSPUK	株式分割換算係数（pSPUO/pSPUC）   ※株式分割日のみ設定


#--------------------------------------
# 電文のサンプル
#
#
# JSON要求電文
# {
#	"p_no":"2",
#	"p_sd_date":"2022.11.22-14:36:41.028",
#	"sCLMID":"CLMMfdsGetMarketPriceHistory",
#	"sIssueCode":"7071",
#	"sSizyouC":"00",
#	"sJsonOfmt":"5"
# }
#
#
#--------------------------------------
# JSON応答電文
# {
#	"p_sd_date":"2022.11.22-14:36:41.439",
#	"p_no":"2",
#	"p_rv_date":"2022.11.22-14:36:41.332",
#	"p_errno":"0",
#	"p_err":"",
#	"sCLMID":"CLMMfdsGetMarketPriceHistory",
#	"sIssueCode":"7071",
#	"sSizyouC":"00",
#	"aCLMMfdsMarketPriceHistory":
#	[
#	{
#		"sDate":"20191009",
#		"pDOP":"4260",
#		"pDHP":"4450",
#		"pDLP":"4000",
#		"pDPP":"4170",
#		"pDV":"1863400",
#		"pDOPxK":"532.5",
#		"pDHPxK":"556.25",
#		"pDLPxK":"500",
#		"pDPPxK":"521.25",
#		"pDVxK":"14907200"
#	},
# ~~~~~~~~
# ~~~~~~~~
#	{
#		"sDate":"20220929",
#		"pDOP":"2418",
#		"pDHP":"2502",
#		"pDLP":"2380",
#		"pDPP":"2380",
#		"pDV":"187300",
#		"pDOPxK":"2418",
#		"pDHPxK":"2502",
#		"pDLPxK":"2380",
#		"pDPPxK":"2380",
#		"pDVxK":"187300",
#		"pSPUK":"0.5",
#		"pSPUO":"1",
#		"pSPUC":"2"
#	},
# ~~~~~~~~
# ~~~~~~~~
#	{
#		"sDate":"20221121",
#		"pDOP":"2921",
#		"pDHP":"2944",
#		"pDLP":"2867",
#		"pDPP":"2926",
#		"pDV":"302800",
#		"pDOPxK":"2921",
#		"pDHPxK":"2944",
#		"pDLPxK":"2867",
#		"pDPPxK":"2926",
#		"pDVxK":"302800"
#	}
#	]
# }

# --- 以上資料 --------------------------------------------------------


# 機能: タイトル行を株価情報のファイルに書き込む
# 引数1: 出力ファイル名
# 備考: 指定ファイルを開き、１行目に項目コード、２行目に項目名を書き込む。
def func_write_daily_price_title(str_fname_output):
    try:
        with open(str_fname_output, 'w', encoding = 'utf-8-sig') as fout:
            print('file open at w, "fout": ', str_fname_output )
            # 項目コード
            str_text_out = ''
            str_text_out = str_text_out + 'sDate' + ','
            str_text_out = str_text_out + 'pDOP' + ','
            str_text_out = str_text_out + 'pDHP' + ','
            str_text_out = str_text_out + 'pDLP' + ','
            str_text_out = str_text_out + 'pDPP' + ','
            str_text_out = str_text_out + 'pDV' + ','
            str_text_out = str_text_out + 'pDOPxK' + ','
            str_text_out = str_text_out + 'pDHPxK' + ','
            str_text_out = str_text_out + 'pDLPxK' + ','
            str_text_out = str_text_out + 'pDPPxK' + ','
            str_text_out = str_text_out + 'pDVxK' + ','
            str_text_out = str_text_out + 'pSPUO' + ','
            str_text_out = str_text_out + 'pSPUC' + ','
            str_text_out = str_text_out + 'pSPUK' + '\n'
            fout.write(str_text_out)     # １行目に列名を書き込む

            # 項目名
            str_text_out = ''
            str_text_out = str_text_out + '日付（YYYYMMDD）' + ','
            str_text_out = str_text_out + '始値' + ','
            str_text_out = str_text_out + '高値' + ','
            str_text_out = str_text_out + '安値' + ','
            str_text_out = str_text_out + '終値' + ','
            str_text_out = str_text_out + '出来高' + ','
            str_text_out = str_text_out + '始値（分割調整済み）' + ','
            str_text_out = str_text_out + '高値（分割調整済み）' + ','
            str_text_out = str_text_out + '安値（分割調整済み）' + ','
            str_text_out = str_text_out + '終値（分割調整済み）' + ','
            str_text_out = str_text_out + '出来高（分割調整済み）' + ','
            str_text_out = str_text_out + '株式分割前単位' + ','
            str_text_out = str_text_out + '株式分割後単位' + ','
            str_text_out = str_text_out + '株式分割換算係数（pSPUO/pSPUC）' + '\n'
            fout.write(str_text_out)     # １行目に列名を書き込む

    except IOError as e:
        print('Can not Write!!!')
        print(type(e))


# 機能: 取得した株価情報を追記モードでファイルに書き込む
# 引数1: 出力ファイル名
# 引数2: 取得した株価情報（リスト型）
# 備考:
#   指定ファイルを開き、1〜2行目に取得する情報名を書き込み、3行目以降で取得した情報を書き込む。
#   pSPUO,pSPUC,pSPUK は株式分割日（権利落ち日)のみデータが返る。通常は項目自体返らない。
def func_write_daily_price(str_fname_output, list_return):
    try:
        with open(str_fname_output, 'a', encoding = 'utf-8-sig') as fout:
            print('file open at a, "fout": ', str_fname_output )
            # 取得した情報から行データを作成し書き込む
            str_text_out = ''
            
            # 日足データを取得できた場合。
            if list_return != None :
                for i in range(len(list_return)):
                    # 行データ作成
                    str_text_out = list_return[i].get("sDate")
                    str_text_out = str_text_out + ',' + list_return[i].get("pDOP")
                    str_text_out = str_text_out + ',' + list_return[i].get("pDHP")
                    str_text_out = str_text_out + ',' + list_return[i].get("pDLP")
                    str_text_out = str_text_out + ',' + list_return[i].get("pDPP")
                    str_text_out = str_text_out + ',' + list_return[i].get("pDV")
                    str_text_out = str_text_out + ',' + list_return[i].get("pDOPxK")
                    str_text_out = str_text_out + ',' + list_return[i].get("pDHPxK")
                    str_text_out = str_text_out + ',' + list_return[i].get("pDLPxK")
                    str_text_out = str_text_out + ',' + list_return[i].get("pDPPxK")
                    str_text_out = str_text_out + ',' + list_return[i].get("pDVxK")
                    # pSPUO,pSPUC,pSPUK は株式分割日（権利落ち日)のみ設定される。
                    if not list_return[i].get("pSPUO") ==  None:
                        str_text_out = str_text_out + ',' + list_return[i].get("pSPUO")
                        str_text_out = str_text_out + ',' + list_return[i].get("pSPUC")
                        str_text_out = str_text_out + ',' + list_return[i].get("pSPUK")
                    str_text_out = str_text_out + '\n'

                    fout.write(str_text_out)     # 処理済みの株価データをファイルに書き込む
                    
            # 日足データを取得できない場合。
            else :
                str_text_out = '日足データがありません。\n'
                print(str_text_out)
                fout.write(str_text_out)     # 処理済みの株価データをファイルに書き込む


    except IOError as e:
        print('Can not Write!!!')
        print(type(e))
        



    
    
# ======================================================================================================
#     プログラム始点 
# ======================================================================================================
# 必要な設定項目
# 銘柄コード: S_ISSUE_CODE （通常銘柄は4桁、優先株等は5桁。例、伊藤園'2593'、伊藤園優先株'25935'）
# 市場: S_SIZYOU_C （00:東証   現在(2021/07/01)、東証のみ可能。）
# 出力ファイル名: FNAME_OUTPUT  （デフォルトは、'price_list_[銘柄コード].csv'）
if __name__ == "__main__":

    # 表示形式を接続情報ファイルから読み込む。
    dic_url_info = func_get_url_info(FNAME_URL_INFO)
    str_sJsonOfmt = dic_url_info.get("sJsonOfmt")

    # ログイン応答を保存した「file_login_response.txt」から、仮想URLと口座情報を取得
    dic_login_property = func_get_login_response(FNAME_LOGIN_RESPONSE)

    # 現在（前回利用した）のp_noをファイルから取得する
    my_p_no = func_get_p_no(FNAME_INFO_P_NO)
    my_p_no = my_p_no + 1
    # 更新した"p_no"を保存する。
    func_save_p_no(FNAME_INFO_P_NO, my_p_no)
    
    print()
    print('-- 株価 日足取得  -------------------------------------------------------------')
    # API要求項目のセット
    dic_req_item = {
        'p_no':                 str(my_p_no),
        'p_sd_date':            func_p_sd_date(),

        'sCLMID':               'CLMMfdsGetMarketPriceHistory', # 新規注文を指示。
        'sIssueCode':           S_ISSUE_CODE,                   # 10.銘柄コード
        'sSizyouC':             S_SIZYOU_C,                     # 11.市場           00:東証   現在(2021/07/01)、東証のみ可能。
        'sJsonOfmt':            str_sJsonOfmt                   # 表示形式（サポートへの問い合わせでは'5'を指定指定した送信電文と受信電文で。）
    }

    # 'CLMMfdsGetMarketPriceHistory'は、仮想URL:'sUrlPrice'
    str_connection_url = dic_login_property.get('sUrlPrice')
    # API問い合わせ実行
    dic_return = func_api_request_from_dic(
                                                False,                  # ログインFlag。    login:true   login以外:false
                                                str_connection_url,     # 接続先URL。
                                                                        #    ログイン時は、FNAME_URL_INFOから取得する接続先。
                                                                        #   それ以外はログインレスポンスで指定される仮想URL。
                                                dic_req_item            # API要求項目
                                            )

    if dic_return is None:
        print('API接続自体の失敗')
        print('JSON形式の受信電文ではありません。接続先も含めて送信電文、受信電文を確認してください。')
    else:
        if dic_return.get('p_errno') != '-2' and dic_return.get('p_errno') != '2':
            # 日足株価部分をリスト型で抜き出す。
            my_list_price = dic_return.get('aCLMMfdsMarketPriceHistory')

            if my_list_price is not None:
                # 出力ファイルにタイトル行を書き込む。
                func_write_daily_price_title(FNAME_OUTPUT)
                
                # 取得した株価情報を追記モードでファイルに書き込む。
                func_write_daily_price(FNAME_OUTPUT, my_list_price)
            else:
                print('日足株価を取得できませんでした。')
                print('銘柄コードを確認してください。')
                print('銘柄コードの変数: S_ISSUE_CODE')
                print()

        elif dic_return.get('p_errno') == '-2' :
            print()
            print('p_errno', dic_return.get('p_errno'))
            print('p_err', dic_return.get('p_err'))
            print("パラメーターの設定に誤りが有ります。")

        # 仮想URLが無効になっている場合
        # if dic_return.get('p_errno') == '2':
        else:
            print()
            print('p_errno', dic_return.get('p_errno'))
            print('p_err', dic_return.get('p_err'))
            print("仮想URLが有効ではありません。")
            print("e_api_login_pubkey.py")
            print("の実行を再度行い、新しく仮想URL（1日券）を取得してください。")
                    
    print()    
    print()
    # 最終の'p_no'を保存する。
    func_save_p_no(FNAME_INFO_P_NO, my_p_no)
