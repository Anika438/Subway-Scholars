let activeSprint = null;
let sprintEndTime = null;

// Initialize state from storage on startup
chrome.storage.local.get(['activeSprint', 'endTime'], (data) => {
    if (data.activeSprint && data.endTime && data.endTime > Date.now()) {
        activeSprint = data.activeSprint;
        sprintEndTime = data.endTime;
        updateBadge("ON", "#FF9800");
    } else {
        clearSprint();
    }
});

function updateBadge(text, color) {
    chrome.action.setBadgeText({ text: text });
    if (color) {
        chrome.action.setBadgeBackgroundColor({ color: color });
    }
}

function clearSprint() {
    activeSprint = null;
    sprintEndTime = null;
    updateBadge("", null);
    chrome.storage.local.remove(['activeSprint', 'endTime']);
    chrome.alarms.clear("sprint_end");
    checkedTitles.clear();
}

// Listen for messages from the popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "sprint_started") {
        chrome.storage.local.get(['activeSprint'], (data) => {
            activeSprint = data.activeSprint;
            sprintEndTime = request.endTime;
            updateBadge("ON", "#FF9800");

            // Set an alarm to clear the sprint when time is up
            const delayInMinutes = Math.max(0.1, (sprintEndTime - Date.now()) / 60000);
            chrome.alarms.create("sprint_end", { delayInMinutes: delayInMinutes });
        });
    } else if (request.action === "sprint_ended") {
        clearSprint();
    }
});

// Handle alarm going off
chrome.alarms.onAlarm.addListener(async (alarm) => {
    if (alarm.name === "sprint_end") {
        clearSprint();

        // Optional: Trigger a browser notification that the sprint is over
        chrome.notifications.create({
            type: "basic",
            iconUrl: "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=", // empty pixel
            title: "Subway Scholars",
            message: "Sprint Completed! Great job focusing."
        });
    } else if (alarm.name.startsWith("check_tab_")) {
        const tabId = parseInt(alarm.name.replace("check_tab_", ""));

        // MV3 Service Worker might have slept and lost memory state
        if (!activeSprint) {
            const data = await chrome.storage.local.get(['activeSprint', 'endTime']);
            if (data.activeSprint && data.endTime && data.endTime > Date.now()) {
                activeSprint = data.activeSprint;
                sprintEndTime = data.endTime;
            } else {
                return; // Sprint ended
            }
        }

        let currentTab = null;
        let checkTitle = "";
        let checkKey = "";

        try {
            currentTab = await chrome.tabs.get(tabId);
            if (!currentTab || !currentTab.url) return;

            const currentUrl = new URL(currentTab.url);
            if (currentUrl.protocol === "chrome-extension:") return;

            const stillDistracting = distractingDomains.some(domain => currentUrl.hostname.includes(domain));
            if (!stillDistracting) return; // User navigated away

            // Okay, they have been on a distracting site for 15s. Time to evaluate.
            checkTitle = currentTab.title;
            checkKey = `${tabId}-${checkTitle}`;
            if (checkedTitles.has(checkKey)) return;

            console.log(`Grace period over! AI evaluating: ${checkTitle}`);
            checkedTitles.add(checkKey);

            const response = await fetch("http://127.0.0.1:8000/api/brain/filter_window", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ window_title: checkTitle, current_topic: activeSprint.suggested_topic })
            });

            if (response.ok) {
                const data = await response.json();
                if (!data.is_relevant) {
                    checkedTitles.delete(checkKey);
                    blockTab(tabId, currentTab.url);
                } else {
                    console.log(`Allowed relevant tab: ${checkTitle}`);
                }
            } else {
                console.error("Response not OK", response.status);
                checkedTitles.delete(checkKey);
                blockTab(tabId, currentTab.url);
            }
        } catch (err) {
            console.error("AI check failed after 15s, defaulting to block", err);
            if (checkKey) checkedTitles.delete(checkKey);
            if (currentTab && currentTab.url) {
                blockTab(tabId, currentTab.url);
            }
        }
    }
});

// Keep track of titles we've explicitly checked so we don't spam the API
const checkedTitles = new Set();
const distractingDomains = ["youtube.com", "facebook.com", "instagram.com", "twitter.com", "reddit.com", "tiktok.com"];

chrome.tabs.onUpdated.addListener(async (tabId, changeInfo, tab) => {
    // MV3 Service Worker might have slept and lost memory state
    if (!activeSprint) {
        const data = await chrome.storage.local.get(['activeSprint', 'endTime']);
        if (data.activeSprint && data.endTime && data.endTime > Date.now()) {
            activeSprint = data.activeSprint;
            sprintEndTime = data.endTime;
        }
    }

    if (!activeSprint || !tab.url) return;

    // Ignore internal extension pages
    if (tab.url.startsWith("chrome-extension:")) return;

    const url = new URL(tab.url);
    const isDistractingSite = distractingDomains.some(domain => url.hostname.includes(domain));

    if (isDistractingSite) {
        // Start 15s grace period timer if not already running via alarms
        const alarmName = `check_tab_${tabId}`;
        const existingAlarm = await chrome.alarms.get(alarmName);
        if (!existingAlarm) {
            console.log(`Setting alarm for tab ${tabId}`);
            chrome.alarms.create(alarmName, { delayInMinutes: 0.25 }); // 15 seconds
        }
    } else {
        // If it's not a distracting site, clear any pending timer
        chrome.alarms.clear(`check_tab_${tabId}`);
    }
});

// Also check when tab becomes active
chrome.tabs.onActivated.addListener(async (activeInfo) => {
    if (!activeSprint) return;
    try {
        const tab = await chrome.tabs.get(activeInfo.tabId);
        if (!tab || !tab.url || tab.url.startsWith("chrome-extension:")) return;
        const url = new URL(tab.url);
        const isDistractingSite = distractingDomains.some(domain => url.hostname.includes(domain));
        if (isDistractingSite) {
            const alarmName = `check_tab_${activeInfo.tabId}`;
            const existingAlarm = await chrome.alarms.get(alarmName);
            if (!existingAlarm) {
                chrome.alarms.create(alarmName, { delayInMinutes: 0.25 });
            }
        }
    } catch (e) {
        // Tab might be closed during fetching
    }
});

chrome.tabs.onRemoved.addListener((tabId) => {
    chrome.alarms.clear(`check_tab_${tabId}`);
});

function blockTab(tabId, originalUrl) {
    const blockUrl = chrome.runtime.getURL(`blocked.html?url=${encodeURIComponent(originalUrl)}&topic=${encodeURIComponent(activeSprint.suggested_topic)}`);
    chrome.tabs.update(tabId, { url: blockUrl });
}
