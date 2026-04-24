document.addEventListener("DOMContentLoaded", () => {
    console.log("Admission Portal loaded");
});

function showPopup(message, type) {
    const popup = document.createElement("div");
    popup.className = "popup-message " + (type === "success" ? "popup-success" : "popup-error");
    popup.textContent = message;

    document.body.appendChild(popup);

    setTimeout(() => popup.classList.add("show"), 100);
    setTimeout(() => {
        popup.classList.remove("show");
        setTimeout(() => popup.remove(), 300);
    }, 2500);
}

document.addEventListener("DOMContentLoaded", function () {
    const container = document.getElementById("flash-data");
    if (!container) return;

    const messages = JSON.parse(container.dataset.messages || "[]");

    messages.forEach(function ([category, message]) {
        showPopup(message, category);
    });
});


function togglePassword(icon) {
    const input = document.getElementById("password");

    if (input.type === "password") {
        input.type = "text";
        icon.classList.remove("hide");
    } else {
        input.type = "password";
        icon.classList.add("hide");
    }
}

document.addEventListener("DOMContentLoaded", function () {
    const currentUrl = window.location.pathname;
    const links = document.querySelectorAll('.sidebar a');

    links.forEach(link => {
        const linkPath = new URL(link.href).pathname;
        if (linkPath === currentUrl) {
            link.classList.add('active');
        }
    });
});

// remark card 

function openRemarkModal(btn) {
    const leadId = btn.dataset.leadId;
    const remark = btn.dataset.remark || "";
    const updated = btn.dataset.updated || "";

    document.getElementById("lead_id").value = leadId;
    document.getElementById("remark").value = remark;

    document.getElementById("remarkUpdated").innerText =
        updated ? `Last updated: ${updated}` : "No previous remark";

    document.getElementById("remarkModal").style.display = "flex";
}

function closeRemarkModal() {
    document.getElementById("remarkModal").style.display = "none";
}

// Signup Button for partner

function toggleSignupOption() {
    const roleSelect = document.getElementById("roleSelect");
    const signupDiv = document.getElementById("partnerSignupOption");

    if (!roleSelect || !signupDiv) return;

    const role = roleSelect.value;

    signupDiv.style.display = role === "partner" ? "block" : "none";
}

// Run on page load (in case partner is preselected)
document.addEventListener("DOMContentLoaded", function () {
    toggleSignupOption();
});


// Leads upload card
function openModal() {
    document.getElementById("uploadModal").style.display = "flex";
}

function closeModal() {
    document.getElementById("uploadModal").style.display = "none";
}

// Close if clicked outside card
window.onclick = function (event) {
    let modal = document.getElementById("uploadModal");
    if (event.target === modal) {
        closeModal();
    }
}

// Auto Show Employee Name
const employeeSelect = document.getElementById("employeeSelect");
if (employeeSelect) {
    employeeSelect.addEventListener("change", function () {
        let selectedOption = this.options[this.selectedIndex];
        let name = selectedOption.getAttribute("data-name");

        const employeeNameInput = document.getElementById("employeeName");
        if (employeeNameInput) {
            employeeNameInput.value = name || "";
        }
    });
}
// -------------------



const popup = document.getElementById("schemePopup");
if (popup) {

    if (sessionStorage.getItem("schemePopupClosed") === "true") {
        popup.remove();
    } else {

        const slidesContainer = document.getElementById("slidesContainer");
        const slides = slidesContainer.querySelectorAll(".slide");

        console.log("Slides found:", slides.length);

        if (slides.length > 1) {

            let currentIndex = 0;

            setInterval(function () {

                currentIndex = (currentIndex + 1) % slides.length;

                slidesContainer.style.transform =
                    `translateX(-${currentIndex * 100}%)`;

                console.log("Sliding to:", currentIndex);

            }, 3000);

        }

    }
}

function closePopup() {
    sessionStorage.setItem("schemePopupClosed", "true");
    const popup = document.getElementById("schemePopup");
    if (popup) popup.remove();
}


// state and city 

document.addEventListener("DOMContentLoaded", function () {

    const stateData = JSON.parse(
        document.getElementById("state-data").textContent
    );

    const stateSelect = document.getElementById("state");
    const districtSelect = document.getElementById("district");

    stateSelect.addEventListener("change", function () {
        const selectedState = this.value.trim();

        districtSelect.innerHTML = '<option value="">Select District</option>';

        if (stateData[selectedState]) {
            stateData[selectedState].forEach(function (district) {
                let option = document.createElement("option");
                option.value = district;
                option.textContent = district;
                districtSelect.appendChild(option);
            });
        }
    });

});