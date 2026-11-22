// Serves the static site in public/ and adds Google Tag Manager to the HTML pages
// when the GTM_ID variable is set in Cloudflare (Settings > Variables and Secrets).
// Without GTM_ID, and on *.workers.dev (branch previews of Workers Builds share the
// variables of production), the pages are served unchanged.

const GTM_ID_PATTERN = /^GTM-[A-Z0-9]+$/;

function headSnippet(id) {
  return `
<!-- Google Tag Manager -->
<script>(function(w,d,s,l,i){w[l]=w[l]||[];w[l].push({'gtm.start':
new Date().getTime(),event:'gtm.js'});var f=d.getElementsByTagName(s)[0],
j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;j.src=
'https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);
})(window,document,'script','dataLayer','${id}');</script>
<!-- End Google Tag Manager -->`;
}

function bodySnippet(id) {
  return `<!-- Google Tag Manager (noscript) -->
<noscript><iframe src="https://www.googletagmanager.com/ns.html?id=${id}"
height="0" width="0" style="display:none;visibility:hidden"></iframe></noscript>
<!-- End Google Tag Manager (noscript) -->
`;
}

export default {
  async fetch(request, env) {
    const response = await env.ASSETS.fetch(request);
    const id = (env.GTM_ID || '').trim();
    const type = response.headers.get('Content-Type') || '';
    // The ID goes into a script: accept only the GTM format.
    const host = new URL(request.url).hostname;
    if (!GTM_ID_PATTERN.test(id) || !type.startsWith('text/html') || host.endsWith('.workers.dev')) {
      return response;
    }
    const rewritten = new HTMLRewriter()
      // Right after <meta charset>, which must stay at the top of <head>.
      .on('meta[charset]', { element(el) { el.after(headSnippet(id), { html: true }); } })
      .on('body', { element(el) { el.prepend(bodySnippet(id), { html: true }); } })
      .transform(response);
    // The asset ETag describes the file without the tag: drop it, so a change of
    // GTM_ID is not hidden by a 304 from the browser cache.
    const out = new Response(rewritten.body, rewritten);
    out.headers.delete('ETag');
    return out;
  },
};
