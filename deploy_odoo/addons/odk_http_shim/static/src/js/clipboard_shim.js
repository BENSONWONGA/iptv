/* 奥登科·HTTP环境兼容垫片
 * 浏览器仅在安全上下文(HTTPS/localhost)提供 navigator.clipboard，
 * 纯 HTTP(IP直连) 下该 API 为 undefined，导致 Odoo20 web_tour 组件加载崩溃。
 * 此处在页面最早期补一个空实现，保证组件正常加载。 */
(function () {
    "use strict";
    if (navigator.clipboard) {
        return;
    }
    var fakeClipboard = {
        writeText: function () { return Promise.resolve(); },
        readText: function () { return Promise.resolve(""); },
        write: function () { return Promise.resolve(); },
        read: function () { return Promise.resolve(); },
    };
    try {
        Object.defineProperty(navigator, "clipboard", {
            value: fakeClipboard,
            configurable: true,
            writable: true,
        });
    } catch (e) {
        try {
            var proto = Object.getPrototypeOf(navigator);
            Object.defineProperty(proto, "clipboard", {
                value: fakeClipboard,
                configurable: true,
            });
        } catch (e2) {
            // 忽略：极旧浏览器
        }
    }
})();
