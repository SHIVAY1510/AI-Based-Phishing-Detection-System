async function loadDashboard() {
    try {
        const res = await fetch("/dashboard-data");  // IMPORTANT: backend API

        if (res.status === 401) {
            document.getElementById("msg").innerHTML = "You must login first.";
            window.location.href = "login.html";
            return;
        }

        const data = await res.json();

        // Summary stats
        document.getElementById("stats").innerHTML = `
            <p><b>Total URLs:</b> ${data.total}</p>
            <p><b>Safe:</b> ${data.safe}%</p>
            <p><b>Phishing:</b> ${data.phishing}%</p>
            <p><b>Other:</b> ${data.other}%</p>
        `;

        // Recent table data
        let rows = "";
        data.recent.forEach(r => {
            rows += <tr><td>${r.url}</td><td>${r.result}</td></tr>;
        });
        document.getElementById("recent").innerHTML = rows;

        // PIE CHART
        new Chart(document.getElementById("pieChart"), {
            type: 'pie',
            data: {
                labels: ["Safe", "Phishing", "Other"],
                datasets: [{
                    data: [data.safe, data.phishing, data.other]
                }]
            }
        });

        // BAR CHART
        new Chart(document.getElementById("barChart"), {
            type: 'bar',
            data: {
                labels: ["Safe", "Phishing", "Other"],
                datasets: [{
                    data: [data.safe, data.phishing, data.other]
                }]
            }
        });

    } catch (err) {
        document.getElementById("msg").innerHTML = "Error loading dashboard.";
    }
}

loadDashboard();