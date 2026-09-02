// ================= LOGIN =================

const currentPage = window.location.pathname.split("/").pop() || "index.html";
const API_BASE = window.location.protocol === "file:" ? "http://127.0.0.1:8000" : "";
const isOfflineMode = () => localStorage.getItem("apiToken") === "offline-mode";
if (currentPage !== "index.html" && !localStorage.getItem("apiToken")) {
    window.location.href = "index.html";
}

async function login(event) {

    event.preventDefault();

    const username =
        document.getElementById("username").value;

    const password =
        document.getElementById("password").value;

    if (window.location.protocol === "file:" && username === "admin" && password === "1234") {
        localStorage.setItem("apiToken", "offline-mode");
        window.location.href = "dashboard.html";
        return;
    }

    try {
        const response = await fetch(API_BASE + "/api/login", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ username, password }) });
        if (!response.ok) throw new Error("Invalid login");
        const data = await response.json();
        localStorage.setItem("apiToken", data.token);
        window.location.href = "dashboard.html";
    } catch (error) {
        if (username === "admin" && password === "1234") {
            localStorage.setItem("apiToken", "offline-mode");
            window.location.href = "dashboard.html";
        } else {
            alert("Login failed. Use admin / 1234 or start the backend.");
        }
    }
}

async function apiRequest(path, options) {
    if (isOfflineMode()) throw new Error("Offline mode");
    const headers = Object.assign({ "Content-Type": "application/json" }, (options && options.headers) || {});
    const token = localStorage.getItem("apiToken");
    if (token) headers.Authorization = "Bearer " + token;
    const response = await fetch(API_BASE + path, Object.assign({}, options, { headers }));
    if (!response.ok) throw new Error("API request failed");
    return response.status === 204 ? null : response.json();
}


// ================= SIDEBAR =================

function toggleSidebar() {

    const sidebar =
        document.getElementById("sidebar");

    sidebar.classList.toggle("show");
}

function openSidePanel(event, pageUrl, title) {

    event.preventDefault();

    const panel = document.getElementById("sidePanel");
    const overlay = document.getElementById("sidePanelOverlay");
    const frame = document.getElementById("sidePanelFrame");
    const panelTitle = document.getElementById("sidePanelTitle");

    if (!panel || !overlay || !frame || !panelTitle) return;

    panelTitle.textContent = title;
    frame.src = pageUrl;
    panel.classList.add("open");
    overlay.classList.add("visible");
    panel.setAttribute("aria-hidden", "false");
}

function closeSidePanel() {

    const panel = document.getElementById("sidePanel");
    const overlay = document.getElementById("sidePanelOverlay");
    const frame = document.getElementById("sidePanelFrame");

    if (!panel || !overlay || !frame) return;

    panel.classList.remove("open");
    overlay.classList.remove("visible");
    panel.setAttribute("aria-hidden", "true");
    frame.src = "about:blank";
}

function toggleNotifications(event) {

    event.stopPropagation();
    const panel = document.getElementById("notificationPanel");
    const button = event.currentTarget;
    if (!panel) return;

    const isOpen = panel.classList.toggle("visible");
    panel.setAttribute("aria-hidden", String(!isOpen));
    button.setAttribute("aria-expanded", String(isOpen));
}

function markNotificationsRead(event) {

    event.stopPropagation();
    document.querySelectorAll(".notification-item.unread").forEach(function (item) {
        item.classList.remove("unread");
    });
    const badge = document.querySelector(".notification-number");
    if (badge) badge.style.display = "none";
}

document.addEventListener("click", function (event) {
    const notificationWrap = document.querySelector(".notification-wrap");
    const panel = document.getElementById("notificationPanel");
    if (notificationWrap && panel && !notificationWrap.contains(event.target)) {
        panel.classList.remove("visible");
        panel.setAttribute("aria-hidden", "true");
    }
});


// ================= LOGOUT =================

function logout() {

    localStorage.removeItem("loggedIn");
    localStorage.removeItem("apiToken");

}


// ================= SEARCH =================

const searchInput =
    document.getElementById("searchInput");

if (searchInput) {

    searchInput.addEventListener("keyup", function () {

        const searchValue =
            this.value.toLowerCase();

        const rows =
            document.querySelectorAll("tbody tr");

        rows.forEach(function (row) {

            const text =
                row.textContent.toLowerCase();

            if (text.includes(searchValue)) {

                row.style.display = "";

            } else {

                row.style.display = "none";

            }

        });

    });

}


// ================= STUDENT ACTIONS =================

async function saveStudent(event) {

    event.preventDefault();

    const student = {
        id: Date.now(),
        name: document.getElementById("studentName").value.trim(),
        registrationNumber: document.getElementById("registrationNumber").value.trim(),
        className: document.getElementById("studentClass").value,
        gender: document.getElementById("studentGender").value,
        dateOfBirth: document.getElementById("dateOfBirth").value,
        parentName: document.getElementById("parentName").value.trim(),
        parentPhone: document.getElementById("parentPhone").value.trim(),
        address: document.getElementById("studentAddress").value.trim()
    };

    if (localStorage.getItem("apiToken") === "offline-mode") {
        const students = getStudents();
        students.push(student);
        localStorage.setItem("students", JSON.stringify(students));
        alert("Student saved successfully!");
        window.location.href = "students.html";
        return;
    }

    try {
        await apiRequest("/api/students", { method: "POST", body: JSON.stringify(student) });
        alert("Student submitted successfully!");
        window.location.href = "students.html";
    } catch (error) {
        const students = getStudents();
        students.push(student);
        localStorage.setItem("students", JSON.stringify(students));
        alert("Student saved successfully!");
        window.location.href = "students.html";
    }
}

function getStudents() {

    const savedStudents = localStorage.getItem("students");
    if (savedStudents) return JSON.parse(savedStudents);

    const starterStudents = [
        { id: "001", registrationNumber: "ISS/2026/001", name: "John Michael", gender: "Male", className: "Form I", parentName: "Michael John", parentPhone: "0712345678", dateOfBirth: "2010-01-15", address: "Iyunga" },
        { id: "002", registrationNumber: "ISS/2026/002", name: "Amina Hassan", gender: "Female", className: "Form II", parentName: "Hassan Ali", parentPhone: "0755123456", dateOfBirth: "2009-06-20", address: "Mbeya" }
    ];
    localStorage.setItem("students", JSON.stringify(starterStudents));
    return starterStudents;
}

async function loadStudents() {

    const tableBody = document.getElementById("studentTableBody");
    if (!tableBody) return;

    let students;
    try { students = await apiRequest("/api/students"); } catch (error) { students = getStudents(); }

    tableBody.innerHTML = students.map(function (student) {
        return `<tr>
            <td>${escapeHTML(student.registrationNumber)}</td>
            <td>${escapeHTML(student.name)}</td>
            <td>${escapeHTML(student.gender)}</td>
            <td>${escapeHTML(student.className)}</td>
            <td><span class="status active-status">Active</span></td>
            <td>${escapeHTML(student.parentName || "-")}</td>
            <td><button class="table-action edit-action" onclick="editStudent('${student.id}')"><i class="fa-solid fa-pen"></i> Edit</button> <button class="table-action delete-action" onclick="deleteStudent('${student.id}')"><i class="fa-solid fa-trash"></i> Delete</button></td>
        </tr>`;
    }).join("");
}

function escapeHTML(value) {

    return String(value || "").replace(/[&<>'"]/g, function (character) {
        return { "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[character];
    });
}

async function loadRecentStudents() {

    const tableBody = document.getElementById("recentStudentsBody");
    if (!tableBody) return;

    let students;
    try { students = await apiRequest("/api/students"); } catch (error) { students = getStudents(); }
    students = students.slice(-4).reverse();
    if (!students.length) {
        tableBody.innerHTML = '<tr><td colspan="4" class="empty-state">No student records yet. Add a student to get started.</td></tr>';
        return;
    }

    tableBody.innerHTML = students.map(function (student) {
        return `<tr><td>${escapeHTML(student.name)}</td><td>${escapeHTML(student.registrationNumber)}</td><td>${escapeHTML(student.className)}</td><td><span class="status active-status">Active</span></td></tr>`;
    }).join("");
}

function searchStudents() {

    const searchInput = document.getElementById("searchInput");
    if (searchInput) searchInput.dispatchEvent(new Event("keyup"));
}

function editStudent(id) {

    window.location.href = "students.html?edit=" + encodeURIComponent(id);
}

async function deleteStudent(id) {

    if (confirm("Delete this student?")) {
        try {
            await apiRequest("/api/students/" + encodeURIComponent(id), { method: "DELETE" });
        } catch (error) {
            const students = getStudents();
            localStorage.setItem("students", JSON.stringify(students.filter(function (student) { return String(student.id) !== String(id); })));
        }
        loadStudents();
        loadRecentStudents();
        alert("Student deleted successfully!");
    }
}

async function loadEditStudent() {

    const form = document.getElementById("studentForm");
    if (!form) return;

    const id = new URLSearchParams(window.location.search).get("edit");
    if (!id) return;
    let students;
    try { students = await apiRequest("/api/students"); } catch (error) { students = getStudents(); }
    const student = students.find(function (item) {
        return String(item.id) === String(id);
    });
    if (!student) return;

    form.dataset.studentId = student.id;
    document.getElementById("studentName").value = student.name || "";
    document.getElementById("registrationNumber").value = student.registrationNumber || "";
    document.getElementById("studentClass").value = student.className || "";
    document.getElementById("studentGender").value = student.gender || "";
    document.getElementById("dateOfBirth").value = student.dateOfBirth || "";
    document.getElementById("parentName").value = student.parentName || "";
    document.getElementById("parentPhone").value = student.parentPhone || "";
    document.getElementById("studentAddress").value = student.address || "";
}

async function updateStudent(event) {

    event.preventDefault();
    const form = event.target;
    let students;
    try { students = await apiRequest("/api/students"); } catch (error) { students = getStudents(); }
    const index = students.findIndex(function (student) {
        return String(student.id) === String(form.dataset.studentId);
    });
    if (index === -1) return;

    students[index] = {
        id: students[index].id,
        name: document.getElementById("studentName").value.trim(),
        registrationNumber: document.getElementById("registrationNumber").value.trim(),
        className: document.getElementById("studentClass").value,
        gender: document.getElementById("studentGender").value,
        dateOfBirth: document.getElementById("dateOfBirth").value,
        parentName: document.getElementById("parentName").value.trim(),
        parentPhone: document.getElementById("parentPhone").value.trim(),
        address: document.getElementById("studentAddress").value.trim()
    };
    try { await apiRequest("/api/students/" + encodeURIComponent(form.dataset.studentId), { method: "PUT", body: JSON.stringify(students[index]) }); }
    catch (error) { localStorage.setItem("students", JSON.stringify(students)); }
    alert("Student updated successfully!");
    window.location.href = "students.html";
}

async function saveSettings() {

    const settings = {
        schoolName: document.getElementById("schoolName").value.trim(),
        academicYear: document.getElementById("academicYear").value
    };

    try {
        await apiRequest("/api/settings", { method: "POST", body: JSON.stringify(settings) });
        localStorage.setItem("settings", JSON.stringify(settings));
        alert("Settings saved successfully!");
    } catch (error) {
        localStorage.setItem("settings", JSON.stringify(settings));
        alert("Settings saved successfully!");
    }
}

async function loadSettings() {

    const schoolName = document.getElementById("schoolName");
    const academicYear = document.getElementById("academicYear");
    if (!schoolName || !academicYear) return;

    let settings;
    try {
        settings = await apiRequest("/api/settings");
    } catch (error) {
        settings = JSON.parse(localStorage.getItem("settings") || "null");
    }
    if (!settings) return;

    schoolName.value = settings.schoolName || schoolName.value;
    academicYear.value = settings.academicYear || academicYear.value;
}

async function saveTeacher(event) {

    event.preventDefault();
    const teacher = {
        id: Date.now(),
        name: document.getElementById("teacherName").value.trim(),
        email: document.getElementById("teacherEmail").value.trim(),
        phone: document.getElementById("teacherPhone").value.trim(),
        subject: document.getElementById("teacherSubject").value,
        classes: document.getElementById("teacherClasses").value.trim(),
        role: document.getElementById("teacherRole").value
    };
    try { await apiRequest("/api/teachers", { method: "POST", body: JSON.stringify(teacher) }); }
    catch (error) {
        const teachers = JSON.parse(localStorage.getItem("teachers") || "[]");
        teachers.push(teacher);
        localStorage.setItem("teachers", JSON.stringify(teachers));
    }
    alert("Teacher saved successfully!");
    window.location.href = "teachers.html";
}

async function saveResult(event) {

    event.preventDefault();
    const result = {
        id: Date.now(),
        exam: document.getElementById("examName").value.trim(),
        className: document.getElementById("resultClass").value,
        subject: document.getElementById("resultSubject").value,
        average: document.getElementById("resultAverage").value,
        date: document.getElementById("resultDate").value,
        status: document.getElementById("resultStatus").value
    };
    try { await apiRequest("/api/results", { method: "POST", body: JSON.stringify(result) }); }
    catch (error) {
        const results = JSON.parse(localStorage.getItem("results") || "[]");
        results.push(result);
        localStorage.setItem("results", JSON.stringify(results));
    }
    alert("Results saved successfully!");
    window.location.href = "results.html";
}

async function loadTeachers() {

    const tableBody = document.getElementById("teacherTableBody");
    if (!tableBody) return;
    let teachers;
    try { teachers = await apiRequest("/api/teachers"); } catch (error) { teachers = JSON.parse(localStorage.getItem("teachers") || "[]"); }
    teachers.forEach(function (teacher) {
        tableBody.insertAdjacentHTML("beforeend", `<tr><td>${teacher.name}</td><td>${teacher.subject}</td><td>${teacher.classes}</td><td><span class="status active-status">Active</span></td></tr>`);
    });
}

async function loadResults() {

    const tableBody = document.getElementById("resultTableBody");
    if (!tableBody) return;
    let results;
    try { results = await apiRequest("/api/results"); } catch (error) { results = JSON.parse(localStorage.getItem("results") || "[]"); }
    results.forEach(function (result) {
        tableBody.insertAdjacentHTML("beforeend", `<tr><td>${result.exam}</td><td>${result.className}</td><td>${result.average}%</td><td><span class="status ${result.status === "Draft" ? "inactive-status" : "active-status"}">${result.status}</span></td></tr>`);
    });
}

function setupMergedViews() {

    const view = new URLSearchParams(window.location.search).get("view");
    const editId = new URLSearchParams(window.location.search).get("edit");
    const studentPanel = document.getElementById("studentFormPanel");
    const teacherPanel = document.getElementById("teacherFormPanel");
    const resultPanel = document.getElementById("resultFormPanel");

    if (studentPanel && (view === "add" || editId)) {
        studentPanel.hidden = false;
        if (editId) {
            loadEditStudent();
            document.getElementById("studentForm").onsubmit = updateStudent;
            document.querySelector("#studentForm button[type=submit]").textContent = "Update Student";
        }
    }
    if (teacherPanel && view === "add") teacherPanel.hidden = false;
    if (resultPanel && view === "add") resultPanel.hidden = false;
}

loadStudents();
loadRecentStudents();
setupMergedViews();
loadTeachers();
loadResults();
loadSettings();