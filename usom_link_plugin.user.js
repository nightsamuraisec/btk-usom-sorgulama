// ==UserScript==
// @name         USOM Yasaklı Site Kontrolü (Arayüzlü)
// @namespace    http://tampermonkey.net/
// @version      1.2
// @description  Ziyaret edilen sitenin alan adını USOM/SGB zararlı liste API’siyle kontrol eder ve sağ altta kalıcı bir durum etiketi gösterir.
// @author       nightsamuraisec
// @match        *://*/*
// @grant        GM.xmlHttpRequest
// @grant        GM.addStyle
// @connect      usom.gov.tr
// @connect      siberguvenlik.gov.tr
// @connect      www.siberguvenlik.gov.tr
// @downloadURL  https://raw.githubusercontent.com/nightsamuraisec/btk-usom-sorgulama/main/usom_link_plugin.user.js
// @updateURL    https://raw.githubusercontent.com/nightsamuraisec/btk-usom-sorgulama/main/usom_link_plugin.user.js
// @run-at       document-start
// ==/UserScript==

(function() {
    'use strict';

    // USOM yasaklı URL listesinin adresi
    const USOM_URL = 'https://www.usom.gov.tr/url-list.txt';
    const BANNED_COLOR = '#8b0000'; // Koyu Kırmızı

    // 1. Yasaklı Listeyi Çekme
    GM.xmlHttpRequest({
        method: "GET",
        url: USOM_URL,
        onload: function(response) {
            if (response.status === 200) {
                const bannedListText = response.responseText;
                const bannedHosts = new Set();
                
                // Listeyi satır satır işleme ve Set'e kaydetme (hızlı kontrol için)
                bannedListText.split('\n').forEach(line => {
                    let url = line.trim().toLowerCase();
                    if (url) {
                        try {
                            const { hostname } = new URL(url.startsWith('http') ? url : 'http://' + url);
                            bannedHosts.add(hostname.replace(/^www\./, ''));
                        } catch (e) {
                            bannedHosts.add(url.replace(/^www\./, ''));
                        }
                    }
                });

                // 2. Mevcut Siteyi Kontrol Etme
                checkCurrentSite(bannedHosts);

            } else {
                console.error("USOM listesi indirilemedi. Durum:", response.status);
            }
        },
        onerror: function(response) {
            console.error("USOM listesi çekilirken hata oluştu:", response.error);
        }
    });

    /**
     * Geçerli pencere konumundan temizlenmiş alan adını alır.
     * @param {string} url - Kontrol edilecek tam URL.
     * @returns {string} Normalize edilmiş alan adı.
     */
    function getNormalizedHostname(url) {
         try {
            const { hostname } = new URL(url);
            // 'www.' kısmını kaldırır ve küçük harfe çevirir.
            return hostname.toLowerCase().replace(/^www\./, '');
        } catch (e) {
            return '';
        }
    }


    /**
     * Güncel sitenin yasaklı listede olup olmadığını kontrol eder ve arayüzü günceller.
     * @param {Set<string>} bannedHosts - Yasaklı alan adlarının kümesi (Set).
     */
    function checkCurrentSite(bannedHosts) {
        const currentHostname = getNormalizedHostname(window.location.href);

        if (!currentHostname) {
            return;
        }

        if (bannedHosts.has(currentHostname)) {
            // Yasaklı: Büyük uyarıyı göster ve kırmızı durumu ayarla
            displayBanWarning(currentHostname);
            createStatusIndicator('banned', currentHostname); 
        } else {
             // Güvenli: Yeşil durumu ayarla
             createStatusIndicator('safe', currentHostname);
        }
    }


    /**
     * Sayfanın üst kısmında uyarı mesajı gösterir (Sadece yasaklı siteler için).
     * @param {string} hostname - Yasaklı olduğu tespit edilen alan adı.
     */
    function displayBanWarning(hostname) {
        const warningDiv = document.createElement('div');
        warningDiv.id = 'usom-ban-warning';
        warningDiv.innerHTML = `
            <p><strong>🚨 SİTE UYARISI 🚨</strong></p>
            <p>Bu alan adı (<code>${hostname}</code>) T.C. Ulaştırma ve Altyapı Bakanlığı USOM yasaklı URL listesinde <strong>bulunmaktadır</strong>.</p>
            <p>Lütfen dikkatli olunuz.</p>
            <button onclick="this.parentNode.remove()">Anladım / Kapat</button>
        `;

        // CSS stilleri
        GM.addStyle(`
            #usom-ban-warning {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                background-color: ${BANNED_COLOR};
                color: white;
                text-align: center;
                padding: 15px;
                z-index: 2147483647;
                font-family: Arial, sans-serif;
                font-size: 16px;
                line-height: 1.5;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
                border-bottom: 3px solid orange;
            }
            #usom-ban-warning strong { font-size: 24px; display: block; margin-bottom: 5px; }
            #usom-ban-warning code { background-color: rgba(255, 255, 255, 0.2); padding: 2px 5px; border-radius: 3px; color: white; font-weight: bold; }
            #usom-ban-warning button {
                margin-top: 10px;
                padding: 5px 15px;
                border: 1px solid white;
                background-color: transparent;
                color: white;
                cursor: pointer;
                border-radius: 4px;
                font-weight: bold;
                transition: all 0.2s;
            }
            #usom-ban-warning button:hover { background-color: white; color: ${BANNED_COLOR}; }
        `);

        document.documentElement.appendChild(warningDiv);
    }


    /**
     * Sağ altta kalıcı durum göstergesi (arayüz) oluşturur.
     * @param {('safe'|'banned')} status - Kontrol durumu.
     * @param {string} hostname - Kontrol edilen alan adı.
     */
    function createStatusIndicator(status, hostname) {
        // Genel CSS stilleri ve animasyon
        GM.addStyle(`
            #usom-status-indicator {
                position: fixed;
                bottom: 15px;
                right: 15px;
                padding: 8px 12px;
                border-radius: 5px;
                color: white;
                font-family: Arial, sans-serif;
                font-size: 14px;
                z-index: 2147483647;
                cursor: default;
                opacity: 0.9;
                transition: opacity 0.3s;
                user-select: none;
            }
            #usom-status-indicator:hover { opacity: 1; }
            .usom-safe {
                background-color: #28a745; /* Yeşil */
                border: 1px solid #1e7e34;
            }
            .usom-banned {
                background-color: ${BANNED_COLOR}; /* Koyu Kırmızı */
                border: 1px solid #5a0000;
                animation: pulse-red 1.5s infinite alternate; /* Yasaklı siteler için titreşim efekti */
            }
            @keyframes pulse-red {
              from {box-shadow: 0 0 0 0 rgba(255, 0, 0, 0.7);}
              to {box-shadow: 0 0 0 10px rgba(255, 0, 0, 0);}
            }
            /* Tooltip stilleri */
            #usom-status-indicator .tooltip-text {
                visibility: hidden;
                width: 250px;
                background-color: #333;
                color: #fff;
                text-align: center;
                border-radius: 6px;
                padding: 8px 10px;
                position: absolute;
                z-index: 2147483647;
                bottom: 100%;
                left: 50%;
                margin-left: -125px;
                opacity: 0;
                transition: opacity 0.3s;
                pointer-events: none; /* Tooltip üzerindeki tıklamayı engeller */
            }
            #usom-status-indicator:hover .tooltip-text {
                visibility: visible;
                opacity: 1;
            }
        `);

        const indicatorDiv = document.createElement('div');
        indicatorDiv.id = 'usom-status-indicator';
        
        let message = '';
        let className = '';
        let tooltipText = '';

        if (status === 'safe') {
            className = 'usom-safe';
            message = `✅ USOM Kontrolü: Güvenli`;
            tooltipText = `Alan Adı (${hostname}) USOM listesinde bulunamadı.`;
        } else if (status === 'banned') {
            className = 'usom-banned';
            message = `🛑 USOM Kontrolü: YASAKLI!`;
            tooltipText = `DİKKAT! Alan Adı (${hostname}) USOM yasaklı listesinde bulundu.`;
        }

        indicatorDiv.className = className;
        indicatorDiv.innerHTML = `
            ${message}
            <span class="tooltip-text">${tooltipText}</span>
        `;
        
        document.documentElement.appendChild(indicatorDiv);
    }

})();