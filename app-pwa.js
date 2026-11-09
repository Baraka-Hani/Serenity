(() => {
  const installButton = document.querySelector('#installAppButton');
  const status = document.querySelector('#installStatus');
  const standalone = window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone === true;
  let installPrompt = null;

  if (installButton) {
    installButton.hidden = standalone;
    window.addEventListener('beforeinstallprompt', event => {
      event.preventDefault();
      installPrompt = event;
      installButton.hidden = false;
    });
    window.addEventListener('appinstalled', () => {
      installPrompt = null;
      installButton.hidden = true;
      if (status) status.textContent = 'Serenity was added to your device.';
    });
    installButton.addEventListener('click', async () => {
      if (!installPrompt) {
        if (status) {
          const isAppleMobile = /iphone|ipad|ipod/i.test(window.navigator.userAgent);
          status.textContent = isAppleMobile
            ? 'To install Serenity, open the Share menu and choose “Add to Home Screen”.'
            : 'Use your browser’s Install app or Add to Home Screen option to install Serenity.';
        }
        return;
      }
      const prompt = installPrompt;
      installPrompt = null;
      try {
        await prompt.prompt();
        const result = await prompt.userChoice;
        if (result.outcome === 'accepted') installButton.hidden = true;
      } catch (error) {
        if (status) status.textContent = 'Serenity could not open the installation prompt. Use your browser’s app installation menu instead.';
        console.error('Serenity installation prompt failed:', error);
      }
    });
  }

  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/service-worker.js', { scope: '/' }).catch(error => {
      if (status) status.textContent = 'Offline app support could not start. Check that the site is served over HTTPS or localhost.';
      console.error('Serenity service worker registration failed:', error);
    });
  } else if (status) {
    status.textContent = 'This browser does not support offline app installation.';
  }
})();
