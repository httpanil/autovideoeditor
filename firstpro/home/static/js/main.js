console.log("JS FILE CONNECTED");

document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("videoForm");

    form.addEventListener("submit", function (e) {
        e.preventDefault(); // 🚫 stop reload
        const btn = document.getElementById("submitBtn");
        const btnText = document.getElementById("btnText");
        const spinner = document.getElementById("btnSpinner");

        btn.disabled = true;
        btnText.innerText = "Processing...";
        spinner.style.display = "inline-block";

        let formData = new FormData(form);

        fetch("/", {
            method: "POST",
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            const jobId = data.job_id;

            document.getElementById("result").innerHTML =
                "Processing... Job ID: " + jobId;

            // 🔁 Start checking status
            checkStatus(jobId);
        })
        .catch(error => {
            console.error("Error:", error);
        });
    });
});

function checkStatus(jobId) {

    const interval = setInterval(() => {

        fetch(`/status/${jobId}/`)
        .then(response => response.json())
        .then(data => {

            if (data.status === "completed") {
                const btn = document.getElementById("submitBtn");
                const btnText = document.getElementById("btnText");
                const spinner = document.getElementById("btnSpinner");
                btn.disabled = false;
                btnText.innerText = "Generate Video";
                spinner.style.display = "none";

                clearInterval(interval); // 🔥 IMPORTANT

                document.getElementById("result").innerHTML = `
                    <div class="video-container">
                        <h3>✅ Video Ready!</h3>

                        <div class="video-wrapper">
                            <video controls class="video-control">
                                <source src="${data.video}" type="video/mp4">
                            </video>
                        </div>

                        <a href="${data.video}" download class="download-btn">
                            ⬇️ Download Video
                        </a>
                    </div>
                `;
            }

            else if (data.status === "error") {
                const btn = document.getElementById("submitBtn");
                const btnText = document.getElementById("btnText");
                const spinner = document.getElementById("btnSpinner");
                btn.disabled = false;
                btnText.innerText = "Generate Video";
                spinner.style.display = "none";

                clearInterval(interval); // 🔥 IMPORTANT

                document.getElementById("result").innerHTML =
                    "❌ Error: " + data.error;
            }

            else {
                document.getElementById("result").innerHTML = `
                    <div style="width:300px; margin:auto; text-align:center;">

                        <p>⏳ ${data.message}</p>

                        <div style="background:#eee; border-radius:10px;">
                            <div style="
                                width:${data.progress || 0}%;
                                background:#6a5acd;
                                height:10px;
                            "></div>
                        </div>

                        <p>${data.progress || 0}%</p>

                    </div>
                `;
            }

        })
        .catch(err => {
            clearInterval(interval);
            console.error("Error:", err);
        });

    }, 3000);
}

document.addEventListener("DOMContentLoaded", function () {

    const radios = document.getElementsByName("mode");
    const uploadDiv = document.getElementById("fileUpload");
    const keywordInput = document.querySelector("input[name='keywords']");
    const keywordSection = document.getElementById("keywordSection");

    keywordInput.required = true;

    radios.forEach(radio => {
        radio.addEventListener("change", () => {
            if (radio.value === "manual" && radio.checked) {
                uploadDiv.style.display = "block";
                 keywordSection.style.display = "none";
                keywordInput.required = false;
            } else {
                uploadDiv.style.display = "none";
                keywordSection.style.display = "block";
                keywordInput.required = true;
            }
        });
    });

});