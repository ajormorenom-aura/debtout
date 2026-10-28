/* DebtOut native bridge (iPhone and Android, Capacitor).
   Bundled by esbuild into www/native.js and loaded before the app. In a normal browser it does nothing:
   the app only uses window.DebtOutNative when it exists, and keeps working without it.

   What it gives the app:
   - storage: a copy of the plan in native storage (iOS can clear a web view's localStorage when space runs low)
   - shareFile: save or send the backup through the system share sheet
   - notifications: real payment reminders on the due day, even with the app closed
   - purchases: the Premium subscription through Apple and Google (RevenueCat). The stores decide who gets the
     free month: once per Apple or Google account, whatever e-mail or device is used
   - haptic, onBack (Android back button), onResume, ready (hides the splash screen) */
import { Capacitor, SystemBars, SystemBarsStyle } from "@capacitor/core";
import { Purchases } from "@revenuecat/purchases-capacitor";
import { App } from "@capacitor/app";
import { Filesystem, Directory, Encoding } from "@capacitor/filesystem";
import { Haptics, ImpactStyle, NotificationType } from "@capacitor/haptics";
import { LocalNotifications } from "@capacitor/local-notifications";
import { Preferences } from "@capacitor/preferences";
import { Share } from "@capacitor/share";
import { SplashScreen } from "@capacitor/splash-screen";

const quiet = (p) => Promise.resolve(p).catch(() => {});

if (Capacitor.isNativePlatform()) {
  const platform = Capacitor.getPlatform();
  document.documentElement.classList.add("native", "native-" + platform);
  quiet(SystemBars.setStyle({ style: SystemBarsStyle.Dark }));

  /* Notification calls run one after another so a cancel never lands after the schedule that replaced it. */
  let queue = Promise.resolve();
  const serial = (fn) => (queue = queue.then(fn, fn));

  /* Subscription (RevenueCat). The public SDK keys come from build.py (window.DEBTOUT_CONFIG). */
  const cfg = window.DEBTOUT_CONFIG || {};
  const rcKey = platform === "ios" ? cfg.revenuecatIos : cfg.revenuecatAndroid;
  const entitlement = cfg.entitlement || "premium";
  let rcReady = null, lastPackage = null;
  const rc = () => {
    if (!rcKey) return Promise.reject(new Error("not_configured"));
    if (!rcReady) rcReady = Purchases.configure({ apiKey: rcKey }).then(() => Purchases, (e) => { rcReady = null; throw e; });
    return rcReady;
  };
  const summary = (info) => {
    const e = info && info.entitlements && info.entitlements.active && info.entitlements.active[entitlement];
    return { active: !!e, trial: !!e && e.periodType === "TRIAL", until: e ? e.expirationDate : null, willRenew: !!e && e.willRenew, manageUrl: (info && info.managementURL) || null };
  };
  const cancelled = (e) => !!e && (String(e.code) === "1" || e.userCancelled === true);

  window.DebtOutNative = {
    platform,

    storage: {
      get: (key) => Preferences.get({ key }).then((r) => (r && typeof r.value === "string" ? r.value : null)),
      set: (key, value) => quiet(Preferences.set({ key, value })),
      remove: (key) => quiet(Preferences.remove({ key })),
    },

    /* Resolves "shared" or "cancelled"; rejects if the file could not be written or shared. */
    async shareFile(name, text) {
      const file = await Filesystem.writeFile({ path: name, data: text, directory: Directory.Cache, encoding: Encoding.UTF8 });
      try {
        await Share.share({ title: "Copia de DebtOut", files: [file.uri], dialogTitle: "Guardar copia de DebtOut" });
        return "shared";
      } catch (e) {
        if (/cancel/i.test(String((e && e.message) || e))) return "cancelled";
        throw e;
      }
    },

    haptic(kind) {
      if (kind === "success") return quiet(Haptics.notification({ type: NotificationType.Success }));
      if (kind === "warn") return quiet(Haptics.notification({ type: NotificationType.Warning }));
      return quiet(Haptics.impact({ style: ImpactStyle.Light }));
    },

    notifications: {
      /* "granted", "denied" or "prompt" */
      permission: () => LocalNotifications.checkPermissions().then((r) => r.display, () => "denied"),
      request: () => LocalNotifications.requestPermissions().then((r) => r.display === "granted", () => false),
      /* list: [{ title, body, at: Date }]. Replaces every reminder scheduled before. */
      replace: (list) =>
        serial(async () => {
          await quiet(LocalNotifications.cancelAll());
          if (!list.length) return;
          const perm = await LocalNotifications.checkPermissions().catch(() => ({ display: "denied" }));
          if (perm.display !== "granted") return;
          await LocalNotifications.schedule({
            notifications: list.map((n, i) => ({
              id: i + 1,
              title: n.title,
              body: n.body,
              schedule: { at: n.at, allowWhileIdle: true },
              isExactNotification: false, // a few minutes late is fine; never send people to the "Alarms" settings
              smallIcon: "ic_stat_debtout",
              iconColor: "#8cc63f",
            })),
          });
        }).catch(() => {}),
      clear: () => serial(() => quiet(LocalNotifications.cancelAll())),
    },

    purchases: {
      available: !!rcKey,
      /* { active, trial, until, willRenew, manageUrl } */
      status: () => rc().then((p) => p.getCustomerInfo()).then((r) => summary(r.customerInfo)),
      /* The monthly package: { price: "2,99 €", trial: true|false, trialPeriod: "P1M" }, or null if none is set up.
         trial is true only when this account can still get the free month (Android: the store only offers it
         then; iPhone: Apple's eligibility check; when Apple can't tell, the price without the trial is shown). */
      offer: async () => {
        const p = await rc();
        const current = (await p.getOfferings()).current;
        const pkg = current && (current.monthly || current.availablePackages[0]);
        if (!pkg) return null;
        lastPackage = pkg;
        const prod = pkg.product;
        let trial = false, trialPeriod = "";
        if (platform === "android") {
          const free = prod.defaultOption && prod.defaultOption.freePhase;
          trial = !!free;
          trialPeriod = free && free.billingPeriod ? free.billingPeriod.iso8601 : "";
        } else if (prod.introPrice && prod.introPrice.price === 0) {
          const el = await p.checkTrialOrIntroductoryPriceEligibility({ productIdentifiers: [prod.identifier] }).catch(() => ({}));
          trial = !!el[prod.identifier] && el[prod.identifier].status === 2; // INTRO_ELIGIBILITY_STATUS_ELIGIBLE
          trialPeriod = "P" + prod.introPrice.periodNumberOfUnits + String(prod.introPrice.periodUnit || "").charAt(0);
        }
        return { price: prod.priceString, trial, trialPeriod };
      },
      /* Resolves the new status, or null if the person closed the store's purchase sheet. */
      async buy() {
        const p = await rc();
        if (!lastPackage) await this.offer();
        if (!lastPackage) throw new Error("no_offer");
        try {
          return summary((await p.purchasePackage({ aPackage: lastPackage })).customerInfo);
        } catch (e) {
          if (cancelled(e)) return null;
          throw e;
        }
      },
      restore: () => rc().then((p) => p.restorePurchases()).then((r) => summary(r.customerInfo)),
      /* Anonymous id the assistant server uses to check the subscription with RevenueCat. */
      userId: () => rc().then((p) => p.getAppUserID()).then((r) => r.appUserID),
      manage(url) {
        location.href = url || (platform === "ios" ? "https://apps.apple.com/account/subscriptions"
          : "https://play.google.com/store/account/subscriptions?package=" + encodeURIComponent(cfg.appId || ""));
      },
      onChange: (cb) => { rc().then((p) => p.addCustomerInfoUpdateListener((info) => cb(summary(info)))).catch(() => {}); },
    },

    /* handler() returns true when the app handled the press; otherwise DebtOut goes to the background. */
    onBack(handler) {
      quiet(App.addListener("backButton", () => { if (!handler()) quiet(App.minimizeApp()); }));
    },
    onResume(handler) {
      quiet(App.addListener("resume", handler));
    },
    ready() {
      return quiet(SplashScreen.hide({ fadeOutDuration: 250 }));
    },
  };
}
