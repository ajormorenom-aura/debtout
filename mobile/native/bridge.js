/* DebtOut native bridge (iPhone and Android, Capacitor).
   Bundled by esbuild into www/native.js and loaded before the app. In a normal browser it does nothing:
   the app only uses window.DebtOutNative when it exists, and keeps working without it.

   What it gives the app:
   - storage: a copy of the plan in native storage (iOS can clear a web view's localStorage when space runs low)
   - shareFile: save or send the backup through the system share sheet
   - notifications: real payment reminders on the due day, even with the app closed
   - haptic, onBack (Android back button), onResume, ready (hides the splash screen) */
import { Capacitor, SystemBars, SystemBarsStyle } from "@capacitor/core";
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
