# Team Class Calendar Dashboard — Full Instructions

## What This Is

An interactive HTML dashboard showing the June 2026 class schedule for the AI HR & Marketing team. It is **not** a spreadsheet — it's a colorful, clickable web page with one column per team member, active teaching days only (Mon & Sat are week off and are excluded).

**File location:** `team_calendar_june2026.html`  
**Repo:** `rishee-ops/AI-assistant` → branch `claude/pensive-cannon-cifwgj`

---

## The Team (8 Members)

| Name | Color | Notes |
|---|---|---|
| Rishee Rhudra | Purple `#7C3AED` | Team manager. Schedule not found in CSAT sheet — marked "Check CSAT-ls" |
| Tanisha Malla | Teal `#0891B2` | |
| Chhavi Jindal | Orange `#EA580C` | |
| Omkar Amble | Blue `#2563EB` | |
| Payal Sakaria | Pink `#DB2777` | Full name confirmed |
| Prachi Pandey | Green `#16A34A` | |
| Khusboo Rizwan | Amber `#D97706` | Listed as "Expert" in CSAT data |
| Ananya Joshi | Red `#DC2626` | Newly added — schedule not yet filled in |

---

## Data Source

**Google Sheet (CSAT):** `https://docs.google.com/spreadsheets/d/1Wt0Q0fmHKQywmQX0zngwKNe2h5_2KIGuphgQj8jd6Gk/edit`

Tabs to look at:
- **CSAT -ls** — Live session schedule (Expert Name + Host Name columns)
- **CSAT Sa** — Another schedule tab (same format)

The data in those tabs only has **March 2026** entries. The June 2026 dashboard was built by projecting the weekly repeat pattern from March across June.

---

## Current Schedule in the Dashboard

Active days per week: **Tuesday, Wednesday, Thursday, Friday, Sunday** (Monday & Saturday = week off)

### Tuesday
| Person | Time | Type | Course |
|---|---|---|---|
| Tanisha | 20:00 | Concept | Personal Branding for Corporate Leaders |
| Chhavi | 20:00 | Pre-Rec + Concept | Intl Job Hunt Accelerator Program |
| Payal | 20:00 | Concept | Generative AI for Career Growth (Senior Professionals) |
| Prachi | 19:00 | Outreach | International Business Law |

### Wednesday
| Person | Time | Type | Course |
|---|---|---|---|
| Chhavi | 20:00 | Scheduled | Content Marketing & Strategy |
| Payal | 20:00 | Scheduled | AI for Business Growth / IIT Roorkee AI Cert. |
| Prachi | 20:00 | Pre-Recorded | US Corporate Compliance |

### Thursday
| Person | Time | Type | Course |
|---|---|---|---|
| Omkar | 20:00 | Concept | AI-Driven Marketing & Sales Automation |
| Payal | 20:00 | Mentoring | Startup Generalist & VA Training |
| Prachi | 20:00 | Outreach | US Tax Compliance & Paralegal Work |
| Khusboo | 20:00 | Concept | Startup Generalist & VA Training |

### Friday
| Person | Time | Type | Course |
|---|---|---|---|
| Khusboo | — | Session | Service Business Entrepreneurship |

### Sunday
| Person | Time | Type | Course |
|---|---|---|---|
| Chhavi | 11:00 | Mentoring | Exec. Cert. Course in Support & Operations |
| Omkar | 13:15 | Concept | Remote Freelancing & Profile Building |
| Payal | 16:00 | Mentoring | AI for Business Growth / IIT Roorkee AI Cert. |
| Prachi | 18:00 | Outreach | US Corp Law courses |
| Prachi | 20:00 | Pre-Recorded | US Corp Law courses |

---

## Pending Items (Need Human Input)

### 1. AppSheet Course Names
The manager shared this link to confirm official course names from the AI vertical:
`https://www.appsheet.com/start/ea6d93ac-ba79-4b4e-a0bc-3c91bc479d3e?platform=desktop#appName=NewApp-80371111-25-05-07&view=Verticle`

AppSheet requires Google login, so it cannot be accessed by AI tools automatically. Someone needs to open it, go to the **AI vertical**, find the course names that match what's in the CSAT sheet, and update the `getSchedule()` function in the HTML file accordingly.

### 2. Rishee Rhudra's Schedule
Rishee is in the employee records but does **not appear as Expert or Host** in the CSAT-ls or CSAT-Sa tabs. His column currently shows "📋 Check CSAT-ls for schedule". Someone needs to find his actual classes and fill them in.

### 3. Ananya Joshi's Schedule
Ananya was added as the 8th team member. Her schedule is completely unknown — her column shows "📋 Check CSAT-ls for schedule" as a placeholder. Fill in her actual schedule.

---

## How to Update the Dashboard

Open `team_calendar_june2026.html` and find the `getSchedule()` function (around line 477). Each day has an object with each person's key:

```js
thursday: {
  omkar:   [{ time: '20:00', type: 'Concept',   course: 'AI-Driven Marketing & Sales Automation' }],
  khusboo: [{ time: '20:00', type: 'Concept',   course: 'Startup Generalist & VA Training' }],
  ananya:  [{ note: true, text: '📋 Check CSAT-ls for schedule' }],  // ← replace this
  ...
}
```

To add a real session, replace the `note` object with:
```js
{ time: '20:00', type: 'Concept', course: 'Course Name Here' }
```

Valid `type` values: `Concept`, `Mentoring`, `Outreach`, `PreRecorded`, `Scheduled`, `Session`

To mark someone as free on a day, set their key to `null`.

To add a new team member:
1. Add a color class in the CSS (e.g., `.th-newperson { background: #HEXCOLOR; color: white; }`)
2. Add to the `PEOPLE` array in JS
3. Add to the legend HTML
4. Add a `<th>` in the table header
5. Add their key to every day in `getSchedule()`
6. Update `colspan` in week separator rows (+1 for each new person)

---

## Dashboard Features

- **Sticky header** — stays visible while scrolling
- **Color-coded columns** — each person has their own color
- **Session type badges** — Concept / Mentoring / Outreach / Pre-Recorded / Scheduled / Session
- **Click any card** — opens a detail popup with course name, type, and time
- **TODAY row** — auto-scrolls and pulses on page load (updates based on today's date — hardcoded as Jun 21 for now; to make it dynamic, update the `today: true` flag in the `WEEKS` array)
- **Week separators** — Week 1 through Week 5
- **Mobile responsive** — shrinks header text on small screens

---

## Git Info

- **Repo:** `rishee-ops/AI-assistant`
- **Branch:** `claude/pensive-cannon-cifwgj`
- **File:** `team_calendar_june2026.html`

To push updates:
```bash
git add team_calendar_june2026.html
git commit -m "Update schedule for [person/change description]"
git push
```
