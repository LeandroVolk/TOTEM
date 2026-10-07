const token = sessionStorage.getItem("totem-admin-token") || "";
const headers = token ? {"X-Admin-Token": token} : {};
const get = async (url) => { const r = await fetch(url,{headers}); if(!r.ok) throw new Error("Dados indisponíveis"); return r.json(); };
const text = (v) => v === null || v === undefined ? "indisponível" : String(v);
async function refresh(){
  try {
    const [status, metrics, bundles] = await Promise.all([get("/api/status"),get("/api/metrics"),get("/api/content/bundles")]);
    const runtime=status.runtime;
    document.querySelector("#status").innerHTML=[["Totem",status.service],["Estado",runtime.state],["Câmera",runtime.camera_ok],["MediaPipe",runtime.mediapipe_ok],["Conteúdo",runtime.current_content_bundle?.bundle_id],["Último evento",runtime.last_event]].map(([k,v])=>`<article><h2>${k}</h2><strong>${text(v)}</strong></article>`).join("");
    document.querySelector("#metricas").innerHTML=Object.entries(metrics).map(([k,v])=>`<article><h2>${k.replaceAll("_"," ")}</h2><strong>${text(v)}</strong></article>`).join("");
    document.querySelector("#conteudo").textContent=bundles.map(b=>`${b.bundle_id} ${b.version}${b.active?" (ativo)":""}`).join(" · ") || "Nenhum bundle publicado.";
  } catch(e) { document.querySelector("#aviso").textContent=e.message; }
}
document.querySelectorAll("button[data-action]").forEach(button=>button.addEventListener("click",async()=>{if(!confirm(`Confirma ${button.textContent.toLowerCase()} o Totem?`))return;const r=await fetch(`/api/kiosk/${button.dataset.action}`,{method:"POST",headers});if(!r.ok)alert("Ação não disponível.");refresh();}));
refresh();setInterval(refresh,10000);
