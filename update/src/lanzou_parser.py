
import re
import json
import html
from curl_cffi import requests


class LanzouParser:
    """蓝奏云直链解析器"""

    def __init__(self, url, password=""):
        self.url = url.strip()
        self.password = password.strip()
        self.session = requests.Session()
        self.cookies = {}
        self.domain = self._extract_domain()

    def _extract_domain(self):
        match = re.search(r"https?://([^/]+)", self.url)
        if not match:
            raise ValueError("链接格式错误")
        return match.group(1)

    def _get_headers(self):
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }

    def _solve_waf(self, arg1):
        """纯 Python 逆向 WAF 算法"""
        m = [15, 35, 29, 24, 33, 16, 1, 38, 10, 9, 19, 31, 40, 27, 22, 23, 25, 13, 6, 11, 39, 18, 20, 8, 14, 21, 32, 26, 2, 30, 7, 4, 17, 5, 3, 28, 34, 37, 12, 36]
        q = [''] * 40
        for i in range(min(len(arg1), 40)):
            for j in range(len(m)):
                if m[j] == i + 1:
                    q[j] = arg1[i]
        u = "".join(q)
        p = "3000176000856006061501533003690027800375"
        v = ""
        for i in range(0, min(len(u), len(p)), 2):
            xor_val = int(u[i:i+2], 16) ^ int(p[i:i+2], 16)
            hex_val = hex(xor_val)[2:]
            if len(hex_val) == 1:
                hex_val = '0' + hex_val
            v += hex_val
        return v

    def _fetch_page(self, url, cookies=None, referer=None):
        """通用请求方法"""
        headers = self._get_headers()
        if referer:
            headers["Referer"] = referer
        return self.session.get(url, headers=headers, cookies=cookies or self.cookies, timeout=10)

    def _fetch_post(self, url, data, referer=None):
        """POST 请求方法"""
        headers = {
            'Origin': f"https://{self.domain}",
            'Referer': referer or self.url,
            'X-Requested-With': 'XMLHttpRequest',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        return self.session.post(url, headers=headers, data=data, cookies=self.cookies, timeout=10)

    def _check_invalid(self, html_text):
        """检查是否违规/失效"""
        return 'class="off"' in html_text or "文件取消" in html_text or "不存在" in html_text

    def _extract_filename(self, html_text):
        """提取文件名"""
        title_match = re.search(r"<title>(.*?)</title>", html_text, re.IGNORECASE | re.DOTALL)
        if title_match:
            raw_title = title_match.group(1).strip()
            file_name = re.sub(r'\s*-\s*(蓝奏云|Lanzou).*$', '', raw_title, flags=re.IGNORECASE).strip()
            return html.unescape(file_name)
        return "未知文件名"

    def _extract_ajax_url(self, html_text):
        """提取 ajax URL"""
        ajax_urls = re.findall(r"url\s*:\s*['\"](/?ajaxm\.php[^'\"]+)['\"]", html_text)
        valid_urls = [link for link in ajax_urls if not link.endswith('file=1')]
        return valid_urls[-1] if valid_urls else None

    def _extract_sign(self, html_text):
        """提取 sign"""
        literal_sign_matches = re.findall(r"'sign'\s*:\s*['\"]([^'\"]+)['\"]", html_text)
        valid_signs = [s for s in literal_sign_matches if len(s) > 20]
        if valid_signs:
            return valid_signs[-1]
        var_match = re.search(r"'sign'\s*:\s*([a-zA-Z0-9_]+)", html_text)
        if var_match:
            sign_var = var_match.group(1)
            val_match = re.search(r"var\s+" + sign_var + r"\s*=\s*'([^']+)'", html_text)
            if val_match:
                return val_match.group(1)
        return ""

    def _dive_iframe(self, html_text):
        """潜入 iframe 获取真实页面"""
        iframe_pattern = re.compile(r'<iframe.*?src="([^"]+)".*?></iframe>')
        matches = iframe_pattern.findall(html_text)
        if not matches:
            return None, None
        iframe_src = next((m for m in matches if '/fn?' in m or '/includes/' in m), matches[0])
        if not iframe_src.startswith('/'):
            iframe_src = '/' + iframe_src
        full_url = f"https://{self.domain}{iframe_src}"
        resp = self._fetch_page(full_url, referer=self.url)
        return resp.text, full_url

    def parse(self):
        """执行解析"""
        try:
            resp1 = self._fetch_page(self.url)
            html_text = resp1.text

            # WAF 破解
            arg1_match = re.search(r"var\s+arg1\s*=\s*'([A-F0-9]+)'", html_text)
            if arg1_match:
                acw_cookie = self._solve_waf(arg1_match.group(1))
                self.cookies["acw_sc__v2"] = acw_cookie
                resp1 = self._fetch_page(self.url)
                html_text = resp1.text

            # 检查失效
            if self._check_invalid(html_text):
                return False, "违规文件或文件不存在!", ""

            file_name = self._extract_filename(html_text)
            referer_url = self.url

            # 提取 ajax URL
            ajax_url = self._extract_ajax_url(html_text)

            # 若主页无 API，下潜 iframe
            if not ajax_url:
                iframe_html, referer_url = self._dive_iframe(html_text)
                if iframe_html:
                    ajax_url = self._extract_ajax_url(iframe_html)
                    html_text = iframe_html

            if not ajax_url:
                return False, "提取 API 地址失败（可能是文件夹或风控拦截）", ""

            if not ajax_url.startswith('/'):
                ajax_url = '/' + ajax_url

            # 提取 sign
            sign_val = self._extract_sign(html_text)

            # POST 获取直链
            data = {
                'action': 'downprocess',
                'sign': sign_val,
                'p': self.password,
                'kd': 1,
                'ves': 1
            }

            resp3 = self._fetch_post(f"https://{self.domain}{ajax_url}", data, referer=referer_url)
            res_json = json.loads(resp3.text.strip())

            if res_json.get('zt') != 1:
                return False, res_json.get('inf', '解析被拒绝'), ""

            if str(res_json.get('inf', '')) != '0':
                file_name = html.unescape(res_json.get('inf'))

            full_url = res_json['dom'] + "/file/" + res_json['url']
            self.cookies['down_ip'] = '1'

            # 获取最终跳转 URL
            resp4 = self.session.get(full_url, headers=self._get_headers(), cookies=self.cookies, allow_redirects=False, timeout=10)
            final_url = resp4.headers.get('Location', full_url)

            return True, file_name, final_url

        except Exception as e:
            return False, f"解析失败: {e}", ""


def main():
    share_url = ''
    password = ''

    print(f"[*] 解析链接: {share_url}, 密码: {password}")
    parser = LanzouParser(share_url, password)
    success, name, direct_url = parser.parse()

    if success:
        print(f"成功！\n文件: {name}\n直链： {direct_url}")
    else:
        print(f"失败: {name}")


if __name__ == "__main__":
    main()
