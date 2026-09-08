(function () {
    var root = document.getElementById("stocks-table");
    if (!root) {
        return;
    }
    var exchange = root.getAttribute("data-exchange");
    if (!exchange) {
        return;
    }
    fetch("/stocks/warm?exchange=" + encodeURIComponent(exchange), {
        credentials: "same-origin",
        headers: { Accept: "application/json" },
    });
})();
