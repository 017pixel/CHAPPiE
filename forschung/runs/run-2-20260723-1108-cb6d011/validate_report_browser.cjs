#!/usr/bin/env node
"use strict";

const fs = require("fs");
const path = require("path");
const { pathToFileURL } = require("url");

const modulePath = process.env.PLAYWRIGHT_MODULE;
if (!modulePath) {
  throw new Error("PLAYWRIGHT_MODULE muss auf das lokale Playwright-Modul zeigen.");
}
const { chromium } = require(modulePath);

const projectRoot = "/home/bbecker/CHAPPiE";
const runDir = path.join(
  projectRoot,
  "forschung/runs/run-2-20260723-1108-cb6d011",
);
const qaDir = path.join(runDir, "report-assets/qa");
const processedDir = path.join(runDir, "processed");
const pages = [
  {
    key: "plan",
    file: path.join(projectRoot, "forschung/report/report-plan.html"),
  },
  {
    key: "report",
    file: path.join(
      projectRoot,
      "forschung/report/CHAPPiE-Forschungsbericht-Run-2.html",
    ),
  },
];
const viewports = [
  { key: "1920x1080", width: 1920, height: 1080 },
  { key: "1440x900", width: 1440, height: 900 },
  { key: "1280x720", width: 1280, height: 720 },
  { key: "tablet-1024x768", width: 1024, height: 768 },
  { key: "mobile-390x844", width: 390, height: 844 },
];

fs.mkdirSync(qaDir, { recursive: true });
fs.mkdirSync(processedDir, { recursive: true });

function relativeProject(file) {
  return path.relative(projectRoot, file).split(path.sep).join("/");
}

async function inspectPage(page, spec, viewport) {
  const consoleErrors = [];
  const pageErrors = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  page.on("pageerror", (error) => pageErrors.push(String(error)));

  await page.goto(pathToFileURL(spec.file).href, {
    waitUntil: "load",
    timeout: 30_000,
  });
  await page.waitForTimeout(150);

  const initial = await page.evaluate(() => {
    const root = document.documentElement;
    const body = document.body;
    const originalScrollX = window.scrollX;
    const originalScrollY = window.scrollY;
    window.scrollTo(100_000, originalScrollY);
    const horizontalScrollReachPx = window.scrollX;
    window.scrollTo(originalScrollX, originalScrollY);
    const internalAnchors = [...document.querySelectorAll('a[href^="#"]')];
    const missingAnchors = internalAnchors
      .map((anchor) => anchor.getAttribute("href"))
      .filter((href) => href && href !== "#")
      .filter((href) => !document.getElementById(decodeURIComponent(href.slice(1))));
    const brokenImages = [...document.images]
      .filter((image) => !image.complete || image.naturalWidth === 0)
      .map((image) => image.getAttribute("src") || "(ohne src)");
    const headings = [...document.querySelectorAll("h1,h2,h3,h4")].map(
      (heading) => Number(heading.tagName.slice(1)),
    );
    const headingSkips = [];
    for (let index = 1; index < headings.length; index += 1) {
      if (headings[index] > headings[index - 1] + 1) {
        headingSkips.push(`${headings[index - 1]}→${headings[index]}`);
      }
    }
    const unlabeledButtons = [...document.querySelectorAll("button")].filter(
      (button) =>
        !button.textContent.trim() &&
        !button.getAttribute("aria-label") &&
        !button.getAttribute("title"),
    ).length;
    const imagesWithoutAlt = [...document.images].filter(
      (image) => !image.hasAttribute("alt"),
    ).length;
    const horizontalOffenders = [...document.querySelectorAll("body *")]
      .map((element) => {
        const box = element.getBoundingClientRect();
        return {
          tag: element.tagName.toLowerCase(),
          id: element.id || "",
          className:
            typeof element.className === "string" ? element.className : "",
          left: Math.round(box.left),
          right: Math.round(box.right),
          width: Math.round(box.width),
          overflowX: getComputedStyle(element).overflowX,
          parent:
            element.parentElement?.id ||
            (typeof element.parentElement?.className === "string"
              ? element.parentElement.className
              : element.parentElement?.tagName.toLowerCase()) ||
            "",
          insideTableWrapper: Boolean(element.closest(".table-wrap")),
          insideSvg: Boolean(element.closest("svg")),
        };
      })
      .filter(
        (item) =>
          !item.insideTableWrapper &&
          (item.left < -1 ||
            item.width > root.clientWidth + 1 ||
            item.right > root.clientWidth + 1),
      )
      .sort((first, second) => second.right - first.right)
      .slice(0, 30);
    const tableWrappers = [...document.querySelectorAll(".table-wrap")].map(
      (element) => {
        const box = element.getBoundingClientRect();
        return {
          left: Math.round(box.left),
          right: Math.round(box.right),
          width: Math.round(box.width),
          clientWidth: element.clientWidth,
          scrollWidth: element.scrollWidth,
          overflowX: getComputedStyle(element).overflowX,
        };
      },
    );
    return {
      title: document.title,
      language: root.lang,
      pageOverflowPx: Math.max(root.scrollWidth, body.scrollWidth) - root.clientWidth,
      horizontalScrollReachPx,
      rootOverflowX: getComputedStyle(root).overflowX,
      bodyOverflowX: getComputedStyle(body).overflowX,
      missingAnchors: [...new Set(missingAnchors)],
      brokenImages,
      headingSkips,
      unlabeledButtons,
      imagesWithoutAlt,
      horizontalOffenders,
      tableWrappers,
      detailsCount: document.querySelectorAll("details").length,
      tableCount: document.querySelectorAll("table").length,
      buttonCount: document.querySelectorAll("button").length,
    };
  });

  const interactions = {
    menu: "not-applicable",
    jury: "not-applicable",
    pitch: "not-applicable",
    details: "not-applicable",
    issueFilter: "not-applicable",
    sidebarToggle: "not-applicable",
  };

  if (viewport.width <= 980 && (await page.locator("#menu").count())) {
    await page.locator("#menu").click();
    interactions.menu = await page.evaluate(
      () =>
        document.body.classList.contains("nav-open") &&
        document.querySelector("#menu")?.getAttribute("aria-expanded") === "true",
    );
    await page.keyboard.press("Escape");
    await page.evaluate(() => {
      document.body.classList.remove("nav-open");
      document.querySelector("#menu")?.setAttribute("aria-expanded", "false");
    });
  }

  if (await page.locator("#view").count()) {
    await page.locator("#view").click();
    interactions.jury = await page.evaluate(
      () =>
        document.body.classList.contains("jury") &&
        document.querySelector("#view")?.getAttribute("aria-pressed") === "true",
    );
    await page.locator("#view").click();
  }

  if (await page.locator("#pitchButton").count()) {
    await page.locator("#pitchButton").click();
    interactions.pitch = await page.evaluate(() => {
      if (document.body.classList.contains("pitch")) return true;
      const pitch = document.querySelector("#pitch");
      if (!pitch) return false;
      const box = pitch.getBoundingClientRect();
      return Math.abs(box.top) < window.innerHeight;
    });
    await page.keyboard.press("Escape");
    await page.evaluate(() => {
      document.body.classList.remove("pitch");
      const button = document.querySelector("#pitchButton");
      if (button && button.textContent === "Pitch beenden") {
        button.textContent = "Pitch-Modus";
      }
    });
  }

  if (
    (await page.locator("#expandAll").count()) &&
    (await page.locator("#expandAll").isVisible())
  ) {
    await page.locator("#expandAll").click();
    interactions.details = await page.evaluate(() => {
      const details = [...document.querySelectorAll("details")];
      return details.length > 0 && details.every((item) => item.open);
    });
    await page.locator("#expandAll").click();
  }

  if (await page.locator("#statusFilter").count()) {
    await page.locator("#statusFilter").selectOption({ label: "FIXED" });
    interactions.issueFilter = await page.evaluate(() => {
      const visible = [...document.querySelectorAll("[data-issue]")].filter(
        (row) => !row.hidden,
      );
      return (
        visible.length > 0 &&
        visible.every((row) => row.dataset.status === "FIXED") &&
        /Issues sichtbar/.test(document.querySelector("#issueCount")?.textContent || "")
      );
    });
    await page.locator("#statusFilter").selectOption("");
  }

  if (
    viewport.width > 980 &&
    (await page.locator("#sidebarToggle").count()) &&
    (await page.locator("#sidebarToggle").isVisible())
  ) {
    await page.locator("#sidebarToggle").click();
    interactions.sidebarToggle = await page.evaluate(() =>
      document.body.classList.contains("sidebar-collapsed"),
    );
    await page.locator("#sidebarToggle").click();
  }

  await page.keyboard.press("Tab");
  const focusVisible = await page.evaluate(() => {
    const active = document.activeElement;
    if (!active || active === document.body) return false;
    const style = getComputedStyle(active);
    return (
      style.outlineStyle !== "none" ||
      style.boxShadow !== "none" ||
      style.borderColor !== "rgba(0, 0, 0, 0)"
    );
  });

  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(50);
  const screenshot = path.join(qaDir, `${spec.key}-${viewport.key}.png`);
  await page.screenshot({ path: screenshot, fullPage: false });

  await page.emulateMedia({ media: "print", reducedMotion: "reduce" });
  const printCheck = await page.evaluate(() => {
    const root = document.documentElement;
    const sidebar = document.querySelector(".sidebar");
    const topbar = document.querySelector(".topbar");
    const bodyStyle = getComputedStyle(document.body);
    const horizontalOffenders = [...document.querySelectorAll("body *")]
      .map((element) => {
        const box = element.getBoundingClientRect();
        return {
          tag: element.tagName.toLowerCase(),
          id: element.id || "",
          className:
            typeof element.className === "string" ? element.className : "",
          left: Math.round(box.left),
          right: Math.round(box.right),
          width: Math.round(box.width),
          parent:
            element.parentElement?.id ||
            (typeof element.parentElement?.className === "string"
              ? element.parentElement.className
              : element.parentElement?.tagName.toLowerCase()) ||
            "",
          insideTableWrapper: Boolean(element.closest(".table-wrap")),
        };
      })
      .filter(
        (item) =>
          !item.insideTableWrapper &&
          (item.left < -1 ||
            item.width > root.clientWidth + 1 ||
            item.right > root.clientWidth + 1),
      )
      .sort((first, second) => second.right - first.right)
      .slice(0, 30);
    return {
      overflowPx:
        Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) -
        document.documentElement.clientWidth,
      visibleMain: getComputedStyle(document.querySelector("main")).display !== "none",
      sidebarHidden: !sidebar || getComputedStyle(sidebar).display === "none",
      topbarHidden: !topbar || getComputedStyle(topbar).display === "none",
      bodyBackground: bodyStyle.backgroundColor,
      bodyColor: bodyStyle.color,
      horizontalOffenders,
      tableWrappers: [...document.querySelectorAll(".table-wrap")].map(
        (element) => {
          const box = element.getBoundingClientRect();
          return {
            left: Math.round(box.left),
            right: Math.round(box.right),
            width: Math.round(box.width),
            clientWidth: element.clientWidth,
            scrollWidth: element.scrollWidth,
            overflowX: getComputedStyle(element).overflowX,
          };
        },
      ),
    };
  });

  const failures = [];
  if (!initial.title) failures.push("Dokumenttitel fehlt");
  if (initial.language !== "de") failures.push(`lang=${initial.language || "(leer)"}`);
  if (initial.pageOverflowPx > 1 && initial.horizontalScrollReachPx > 1)
    failures.push(
      `horizontal scrollbar ${initial.horizontalScrollReachPx}px ` +
        `(Inhalt ${initial.pageOverflowPx}px breiter)`,
    );
  const offscreenSvgText = initial.horizontalOffenders.filter(
    (item) => item.tag === "text" && item.insideSvg,
  );
  if (offscreenSvgText.length)
    failures.push(`${offscreenSvgText.length} SVG-Texte außerhalb des Viewports`);
  if (initial.missingAnchors.length)
    failures.push(`${initial.missingAnchors.length} interne Ziele fehlen`);
  if (initial.brokenImages.length)
    failures.push(`${initial.brokenImages.length} Bilder defekt`);
  if (initial.headingSkips.length)
    failures.push(`Überschriftenebenen: ${initial.headingSkips.join(", ")}`);
  if (initial.unlabeledButtons)
    failures.push(`${initial.unlabeledButtons} Buttons ohne Namen`);
  if (initial.imagesWithoutAlt)
    failures.push(`${initial.imagesWithoutAlt} Bilder ohne alt`);
  if (!focusVisible) failures.push("Fokusindikator nicht nachweisbar");
  if (!printCheck.visibleMain) failures.push("Hauptinhalt in Druckansicht verborgen");
  if (!printCheck.sidebarHidden || !printCheck.topbarHidden)
    failures.push("Navigation in Druckansicht nicht verborgen");
  if (printCheck.overflowPx > 1)
    failures.push(`Druckansicht ${printCheck.overflowPx}px horizontal breiter`);
  if (printCheck.bodyBackground !== "rgb(255, 255, 255)")
    failures.push(`Druckhintergrund ${printCheck.bodyBackground} statt weiß`);
  if (printCheck.bodyColor !== "rgb(24, 24, 24)")
    failures.push(`Drucktext ${printCheck.bodyColor} statt dunkel`);
  for (const [name, value] of Object.entries(interactions)) {
    if (value === false) failures.push(`Interaktion ${name} fehlgeschlagen`);
  }
  if (consoleErrors.length) failures.push(`${consoleErrors.length} Konsolenfehler`);
  if (pageErrors.length) failures.push(`${pageErrors.length} Seitenfehler`);

  return {
    document: relativeProject(spec.file),
    viewport,
    initial,
    interactions,
    focusVisible,
    printCheck,
    consoleErrors,
    pageErrors,
    screenshot: relativeProject(screenshot),
    passed: failures.length === 0,
    failures,
  };
}

async function inspectNoJavascript(page, spec) {
  await page.goto(pathToFileURL(spec.file).href, {
    waitUntil: "load",
    timeout: 30_000,
  });
  const state = await page.evaluate(() => {
    const main = document.querySelector("main");
    const mainStyle = main ? getComputedStyle(main) : null;
    return {
      mainPresent: Boolean(main),
      mainVisible: Boolean(mainStyle) && mainStyle.display !== "none",
      visibleTextCharacters: (main?.innerText || "").trim().length,
      headings: document.querySelectorAll("h1,h2,h3").length,
      navigationLinks: document.querySelectorAll('nav a[href^="#"]').length,
      details: document.querySelectorAll("details").length,
    };
  });
  const failures = [];
  if (!state.mainPresent || !state.mainVisible)
    failures.push("Hauptinhalt ohne JavaScript nicht sichtbar");
  if (state.visibleTextCharacters < 5_000)
    failures.push(`nur ${state.visibleTextCharacters} sichtbare Textzeichen`);
  if (state.headings < 10)
    failures.push(`nur ${state.headings} Überschriften`);
  if (state.navigationLinks < 5)
    failures.push(`nur ${state.navigationLinks} Navigationsziele`);
  if (state.details < 1)
    failures.push("keine semantischen Details-Blöcke");
  return {
    document: relativeProject(spec.file),
    viewport: "1440x900",
    javascriptEnabled: false,
    state,
    passed: failures.length === 0,
    failures,
  };
}

async function main() {
  const browser = await chromium.launch({
    headless: true,
    args: ["--disable-gpu", "--no-sandbox"],
  });
  const checks = [];
  const noJavascriptChecks = [];
  try {
    for (const viewport of viewports) {
      const context = await browser.newContext({
        viewport: { width: viewport.width, height: viewport.height },
        colorScheme: "dark",
        reducedMotion: "reduce",
      });
      for (const spec of pages) {
        const page = await context.newPage();
        checks.push(await inspectPage(page, spec, viewport));
        await page.close();
      }
      await context.close();
    }
    const noJavascriptContext = await browser.newContext({
      viewport: { width: 1440, height: 900 },
      colorScheme: "dark",
      reducedMotion: "reduce",
      javaScriptEnabled: false,
    });
    for (const spec of pages) {
      const page = await noJavascriptContext.newPage();
      noJavascriptChecks.push(await inspectNoJavascript(page, spec));
      await page.close();
    }
    await noJavascriptContext.close();
  } finally {
    await browser.close();
  }

  const result = {
    schema_version: 1,
    generated_at: new Date().toISOString(),
    renderer: "Playwright Chromium, headless, --disable-gpu",
    viewports,
    passed:
      checks.every((check) => check.passed) &&
      noJavascriptChecks.every((check) => check.passed),
    passed_checks: checks.filter((check) => check.passed).length,
    total_checks: checks.length,
    checks,
    no_javascript_passed: noJavascriptChecks.filter((check) => check.passed).length,
    no_javascript_total: noJavascriptChecks.length,
    no_javascript_checks: noJavascriptChecks,
  };
  const jsonFile = path.join(processedDir, "browser-report-validation.json");
  fs.writeFileSync(jsonFile, `${JSON.stringify(result, null, 2)}\n`);

  const lines = [
    "# Browser- und Responsive-Validierung",
    "",
    `Zeitpunkt: \`${result.generated_at}\``,
    "",
    `Renderer: ${result.renderer}`,
    "",
    `Ergebnis: **${result.passed_checks}/${result.total_checks} Ansichten bestanden**`,
    "",
    "| Dokument | Viewport | Ergebnis | Feststellungen | Screenshot |",
    "|---|---:|---|---|---|",
    ...checks.map((check) => {
      const findings = check.failures.length
        ? check.failures.join("; ")
        : "Keine automatisiert festgestellten Fehler";
      return `| ${check.document} | ${check.viewport.key} | ${check.passed ? "PASS" : "FAIL"} | ${findings} | \`${check.screenshot}\` |`;
    }),
    "",
    `Ohne JavaScript: **${result.no_javascript_passed}/${result.no_javascript_total} Dokumente lesbar**`,
    "",
    ...noJavascriptChecks.map((check) => {
      const findings = check.failures.length
        ? check.failures.join("; ")
        : "Hauptinhalt, Überschriften, Navigation und Details vorhanden";
      return `- ${check.document}: ${check.passed ? "PASS" : "FAIL"} — ${findings}`;
    }),
    "",
    "## Prüfumfang",
    "",
    "- reale Chromium-Darstellung in fünf verbindlichen Zielgrößen",
    "- Seitenüberlauf einschließlich abgeschnittener SVG-Texte, interne Sprungziele, Bilder und Überschriftenhierarchie",
    "- Menü, Jury-/Pitch-Modus, Details, Issue-Filter und Sidebar (soweit vorhanden)",
    "- Tastaturfokus, reduzierte Bewegung sowie Drucklayout, Druckfarben und ausgeblendete Navigation",
    "- dokumentarische Grundlesbarkeit bei deaktiviertem JavaScript",
    "- JavaScript-, Seiten- und Konsolenfehler",
    "",
    "Die Screenshots werden zusätzlich visuell durch die Hauptinstanz geprüft.",
    "",
  ];
  fs.writeFileSync(
    path.join(processedDir, "browser-report-validation.md"),
    lines.join("\n"),
  );

  console.log(
    JSON.stringify(
      {
        passed: result.passed,
        passed_checks: result.passed_checks,
        total_checks: result.total_checks,
        no_javascript_passed: result.no_javascript_passed,
        no_javascript_total: result.no_javascript_total,
        json: relativeProject(jsonFile),
      },
      null,
      2,
    ),
  );
  process.exitCode = result.passed ? 0 : 1;
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 2;
});
