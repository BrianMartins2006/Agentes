import React, { useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';
import { useIrrigationNotifications } from './irrigationNotifications';

const API = (import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');
const fmt = value => new Date(value).toLocaleString('pt-BR');
const num = (value, digits=1) => Number(value).toLocaleString('pt-BR', {maximumFractionDigits:digits});
const initialDate = () => {const d=new Date(Date.now()-86400000); return new Date(d-d.getTimezoneOffset()*60000).toISOString().slice(0,16);};

function Chart({rows, field, title, unit, color, wide=false}) {
  const data=[...rows].sort((a,b)=>new Date(a.measured_at)-new Date(b.measured_at));
  let content='Nenhuma medição no período selecionado';
  if(data.length) {
    const times=data.map(r=>new Date(r.measured_at).getTime()), values=data.map(r=>r[field]);
    const min=Math.min(...values),max=Math.max(...values),pad=Math.max((max-min)*.12,.5),low=min-pad,high=max+pad;
    const x=t=>58+(t-times[0])/Math.max(times.at(-1)-times[0],60000)*610;
    const y=v=>168-(v-low)/(high-low)*140;
    const segments=[[]]; data.forEach((r,i)=>{if(i && times[i]-times[i-1]>300000)segments.push([]);segments.at(-1).push(`${x(times[i])},${y(r[field])}`);});
    content=<svg viewBox="0 0 700 210" role="img" aria-label={`${title}: ${data.length} amostras, mínimo ${num(min)}, máximo ${num(max)}`}>
      {[0,1,2,3].map(i=>{const value=low+(high-low)*i/3;return <g key={i}><line x1="58" x2="668" y1={y(value)} y2={y(value)} stroke="#2b3c34"/><text x="48" y={y(value)+4} textAnchor="end" fill="#96ada4" fontSize="11">{num(value)}</text></g>;})}
      {segments.map((points,i)=><polyline key={i} points={points.join(' ')} fill="none" stroke={color} strokeWidth="2.2"/>)}
      {data.map((r,i)=><circle key={r.id} cx={x(times[i])} cy={y(r[field])} r={data.length>100?1.3:3} fill={color}><title>{fmt(r.measured_at)} · {num(r[field])}</title></circle>)}
      <text x="58" y="196" fill="#96ada4" fontSize="10">{fmt(data[0].measured_at)}</text><text x="668" y="196" textAnchor="end" fill="#96ada4" fontSize="10">{fmt(data.at(-1).measured_at)}</text>
    </svg>;
  }
  return <article className={`panel chart ${wide?'wide':''}`}><h3>{title} <span>{unit}</span></h3><div className="plot">{content}</div></article>;
}
function Metric({label,value,detail,small=false}) {return <article className="panel metric"><span className="eyebrow">{label}</span><strong className={small?'smaller':''}>{value}</strong><span>{detail}</span></article>;}
function exportCSV(rows) {
  const fields=['device_id','measured_at','received_at','temperature_c','air_humidity_pct','soil_raw'];
  const escape=v=>'"'+String(v).replace(/^[=+@-]/,"'$&").replaceAll('"','""')+'"';
  const csv=[fields.join(','),...rows.map(r=>fields.map(f=>escape(r[f])).join(','))].join('\r\n');
  const url=URL.createObjectURL(new Blob(['\uFEFF'+csv],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download='medicoes.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
function App() {
  const [config,setConfig]=useState(null),[auto,setAuto]=useState(true),[tick,setTick]=useState(0);
  const [state,setState]=useState({rows:[],latest:null,prediction:null,external:null,loading:false,message:'Abra a engrenagem no topo para conectar sua estação.',currentError:false});
  const [formError,setFormError]=useState('');
  const [period,setPeriod]=useState(()=>({since:initialDate(),until:''}));
  const settingsDialog=useRef(null), settingsForm=useRef(null), settingsButton=useRef(null);
  function openSettings() {
    settingsForm.current.reset();
    settingsDialog.current.showModal();
  }
  function closeSettings() {
    settingsDialog.current.close();
    settingsButton.current.focus();
  }
  useEffect(()=>{if(!auto||!config)return;const timer=setInterval(()=>{if(!document.hidden)setTick(v=>v+1);},30000);return()=>clearInterval(timer);},[auto,config]);
  useEffect(()=>{
    if(!config)return;
    const controller=new AbortController();let active=true;
    setState({rows:[],latest:null,prediction:null,external:null,loading:true,message:`Consultando ${config.device}…`,currentError:false});
    async function request(path,params) {
      const timeout=setTimeout(()=>controller.abort(),15000);
      try {const response=await fetch(API+path+'?'+params,{headers:{'X-API-Key':config.key},signal:controller.signal,cache:'no-store'});
        if(!response.ok)throw new Error(response.status===401?'Chave de acesso inválida.':`Erro ${response.status} na API.`);return await response.json();
      } finally {clearTimeout(timeout);}
    }
    const params=new URLSearchParams({device_id:config.device,since:config.since,limit:1000});if(config.until)params.set('until',config.until);
    Promise.allSettled([request('/api/v1/measurements',params),request('/api/v1/measurements',new URLSearchParams({device_id:config.device,limit:1})),request('/api/v1/predictions',new URLSearchParams({device_id:config.device})),request('/api/v1/experiments/soil',new URLSearchParams())]).then(results=>{
      if(!active)return;
      const rows=results[0].status==='fulfilled'?results[0].value:[],latest=results[1].status==='fulfilled'?results[1].value[0]??null:null;
      const prediction=results[2].status==='fulfilled'?results[2].value:{status:'unavailable',reason:'Falha ao consultar o modelo.'};
      const external=results[3].status==='fulfilled'?results[3].value:{status:'unavailable',reason:'Experimento externo indisponível; confira o deploy da API.'};
      const errors=results.slice(0,3).filter(r=>r.status==='rejected').map(r=>r.reason.name==='AbortError'?'Tempo de consulta esgotado.':r.reason.message);
      setState({rows,latest,prediction,external,loading:false,currentError:results[1].status==='rejected',message:errors.length?[...new Set(errors)].join(' '):`${config.device} · Atualizado às ${new Date().toLocaleTimeString('pt-BR')}. ${rows.length===1000?'Limite de 1.000 amostras: reduza o período.':''} Tabela: até 100 linhas; CSV: todas as carregadas.`});
    });
    return()=>{active=false;controller.abort();};
  },[config,tick]);
  function selectedPeriod() {
    const since=new Date(period.since), until=period.until?new Date(period.until):null;
    if(!Number.isFinite(since.getTime()) || (until && (!Number.isFinite(until.getTime()) || since>until))) {
      setFormError('O início deve ser anterior ao fim e as datas devem ser válidas.');return null;
    }
    setFormError('');return {since:since.toISOString(),until:until?.toISOString()};
  }
  function saveSettings(event) {
    event.preventDefault();const dates=selectedPeriod();if(!dates){closeSettings();return;}
    const form=new FormData(event.currentTarget);
    setAuto(form.get('auto')==='on');
    setConfig({device:form.get('device').trim(),key:form.get('key'),...dates});
    closeSettings();
  }
  function applyPeriod(event) {
    event.preventDefault();const dates=selectedPeriod();if(!dates)return;
    if(!config){openSettings();return;}
    setConfig({...config,...dates});
  }
  const {rows,latest,prediction,external,loading}=state;
  const age=latest?(Date.now()-new Date(latest.received_at))/1000:null;
  const status=loading?'Consultando':state.currentError?'Falha de comunicação':!config?'Aguardando conexão':!latest?'Dispositivo sem dados':age < -60?'Relógio inconsistente':age<=300?'Dados atualizados':'Dados atrasados';
  const available=prediction&&['available','experimental'].includes(prediction.status);
  const advice=prediction?.irrigation;
  const notifications=useIrrigationNotifications(advice,config?.device);
  return <><header><a className="brand" href="/">◉ <span>ambiente<span className="brand-dot">.</span></span></a><span className="eyebrow">ESP32 / MONITORAMENTO AMBIENTAL</span><div className="header-actions"><span className={`badge ${status==='Dados atualizados'?'good':'bad'}`}>{status}</span><button ref={settingsButton} type="button" className="settings-button" aria-label="Abrir configurações de conexão" aria-haspopup="dialog" onClick={openSettings} title="Configurações">
      <svg viewBox="0 0 24 24" width="21" height="21" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true"><path d="m9 3-.7 2.4-2 .9L4 5.7 2.5 8.3l1.7 1.8-.2 2.2-1.7 1.8 1.5 2.6 2.4-.6 1.9 1.1.7 2.4h3l.8-2.4 1.9-1.1 2.4.6 1.5-2.6-1.7-1.8-.1-2.2 1.7-1.8-1.5-2.6-2.4.6-2-.9L12 3Z" transform="translate(1 1)"/><circle cx="12" cy="12" r="3"/></svg>
    </button></div></header>
    <dialog ref={settingsDialog} className="settings-dialog" aria-labelledby="settings-title" aria-describedby="settings-description" onClick={e=>{if(e.target===settingsDialog.current){const r=e.target.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)closeSettings();}}}>
      <div className="settings-heading"><div><p className="eyebrow">SUA ESTAÇÃO</p><h2 id="settings-title">Configurações de conexão</h2></div><button type="button" className="close-button" onClick={closeSettings} aria-label="Fechar configurações">×</button></div>
      <p id="settings-description" className="muted">Conecte o dispositivo e escolha como atualizar os dados.</p>
      <form ref={settingsForm} onSubmit={saveSettings} className="settings-form">
        <label>Dispositivo<input name="device" required maxLength="64" pattern="[A-Za-z0-9_-]+" defaultValue={config?.device||'esp32-01'} autoFocus/></label>
        <label>Chave de acesso<input name="key" type="password" required autoComplete="off" placeholder="X-API-Key" defaultValue={config?.key||''}/><small>A chave fica apenas na memória desta página.</small></label>
        <label className="auto"><input name="auto" type="checkbox" defaultChecked={auto}/>Atualizar automaticamente a cada 30 s</label>
        <div className="settings-footer"><button type="button" className="secondary-button" onClick={closeSettings}>Cancelar</button><button type="submit">Salvar e conectar</button></div>
      </form>
    </dialog><main>
    <section className="intro"><div><p className="eyebrow">OBSERVAR. COMPREENDER. ANTECIPAR.</p><h1>Seu ambiente, em perspectiva.</h1><p>Do sensor ao histórico. Acompanhe as condições e antecipe mudanças no solo.</p></div><div className="live-label"><span>●</span> Dados reais da sua estação</div></section>
    <p id="feedback" role="status" aria-live="polite">{formError||state.message}</p>
    <section className="metrics" aria-label="Leituras mais recentes"><Metric label="TEMPERATURA" value={latest?`${num(latest.temperature_c)} °C`:'—'} detail="Graus Celsius · DHT11"/><Metric label="UMIDADE DO AR" value={latest?`${num(latest.air_humidity_pct)} %`:'—'} detail="Umidade relativa · DHT11"/><Metric label="SENSOR DO SOLO" value={latest?num(latest.soil_raw,0):'—'} detail="Leitura bruta · GPIO34"/><Metric label="ÚLTIMA COMUNICAÇÃO" value={status} detail={latest?fmt(latest.received_at):'Sem leitura confirmada'} small/></section>
    <div className="section-title"><div><p className="eyebrow">HISTÓRICO DOS SENSORES</p><h2>Como o ambiente mudou</h2></div><span>{rows.length} amostras carregadas</span></div>
    <form onSubmit={applyPeriod} className="history-filters"><label>Início<input name="since" type="datetime-local" required value={period.since} onChange={e=>setPeriod({...period,since:e.target.value})}/></label><label>Fim<input name="until" type="datetime-local" value={period.until} onChange={e=>setPeriod({...period,until:e.target.value})}/></label><button type="submit" className="secondary-button" disabled={loading}>Aplicar período</button><span className="muted">Fim vazio acompanha o presente</span></form>
    <section className="charts"><Chart rows={rows} field="temperature_c" title="Temperatura" unit="°C" color="#f1bb80"/><Chart rows={rows} field="air_humidity_pct" title="Umidade do ar" unit="%" color="#83c9d4"/><Chart rows={rows} field="soil_raw" title="Leitura do solo" unit="valor bruto" color="#b7f16e" wide/></section>
    <p className="muted">Datas no fuso do navegador. Lacunas maiores que 5 minutos interrompem as linhas. Cartões e previsão mostram o estado mais recente, independente do período filtrado.</p>
    <section className={`panel irrigation-card ${advice?.notify?'irrigation-warning':''}`} aria-label="Orientação de irrigação">
      <div className="section-title"><div><p className="eyebrow">AVISOS AO PRODUTOR · PREVISÃO DO MODELO</p><h2>{advice?.title||'Aguardando avaliação de irrigação'}</h2></div>
        <button type="button" className="secondary-button" onClick={notifications.enable} disabled={!notifications.supported||notifications.permission==='granted'}>{notifications.permission==='granted'?'Avisos do navegador ativados':'Ativar avisos do navegador'}</button>
      </div>
      <p role={advice?.notify?'alert':'status'}>{advice?.message||'Conecte o dispositivo para consultar o modelo e a condição de irrigação.'}</p>
      {advice?.predicted_soil_pct!==undefined&&<p className="muted">Solo atual: {num(advice.current_soil_pct)}% · Previsto: {num(advice.predicted_soil_pct)}% · Umidade do ar: {num(advice.air_humidity_pct)}% · Horário previsto: {fmt(advice.target_at)}</p>}
      <p className="muted">Limites de referência: solo abaixo de {advice?.soil_threshold_pct??30}% e ar abaixo de {advice?.air_threshold_pct??40}%. Ajustar à cultura e validar a calibração. O ar baixo, sozinho, não indica irrigação.</p>
      <p className="muted">{notifications.hint||'As notificações exigem permissão e esta página aberta. Não há envio de WhatsApp/e-mail ou acionamento automático de bomba.'}</p>
    </section>
    <section className="panel prediction"><div><p className="eyebrow">APRENDIZADO DE MÁQUINA · RANDOM FOREST</p><p className="muted">{prediction ? `Treinamento automático ${prediction.automatic_training ? "ativado" : "desativado"}${prediction.trained_at ? ` · Último treino: ${fmt(prediction.trained_at)}` : ""}` : ""}</p><h2>Um olhar para os próximos 30 minutos.</h2><p role="status">{loading?'Consultando modelo…':available?prediction.notice:prediction?.reason||'Conecte a estação para consultar o modelo.'}</p>{available&&<p className="muted">MAE do modelo: {num(prediction.metrics.model_mae,2)} · baseline: {num(prediction.metrics.baseline_mae,2)} (leitura bruta). Modelo {prediction.model_id}. Percentual estimado: {num(prediction.estimated_soil_pct)}% pela calibração do firmware; validar no solo real.</p>}</div><div className="prediction-result"><strong>{available?num(prediction.predicted_soil_raw):'—'}</strong><span>leitura bruta prevista do solo</span>{available&&<span>Para {fmt(prediction.target_at)}</span>}</div></section>
    <section className="panel external-experiment" aria-label="Experimento de solo com dados públicos">
      <p className="eyebrow">EXPERIMENTO SEPARADO · DATASET PÚBLICO · RANDOM FOREST</p><h2>Aprendizado com solo em condições de campo</h2>
      <p className="muted">Este experimento usa dados históricos de outra estação. Não é uma previsão validada para sua ESP32 e não usa a escala bruta 0–4095.</p>
      {external?.status==='external_experiment'?<><p>{external.beats_baseline?'O modelo superou a persistência no teste temporal externo.':'Modelo treinado; não superou a persistência no teste externo. Resultado experimental.'}</p>
        <div className="external-metrics"><div><span>MAE do modelo</span><strong>{num(external.metrics.model_mae,3)} pp</strong></div><div><span>MAE de persistência</span><strong>{num(external.metrics.baseline_mae,3)} pp</strong></div><div><span>Exemplos de treino / teste</span><strong>{num(external.train_samples,0)} / {num(external.test_samples,0)}</strong></div></div>
        <p className="muted">Horizonte: {external.horizon_minutes} minutos · Erros em pontos percentuais (pp) · Estação {external.source.station}, solo a {external.source.depth_cm} cm · <a href="https://zenodo.org/records/21703750" target="_blank" rel="noreferrer">Fonte: Zenodo / Universidade de Ioannina</a> · CC BY 4.0</p>
        <p className="muted">Período de teste: {external.test_start.replace('T',' ')} a {external.test_end.replace('T',' ')} (horários originais, fuso não informado pela fonte).</p>
        {external.test_examples?.length>0&&<div className="table-scroll"><table><caption className="sr-only">Exemplos históricos externos, não leituras da ESP32</caption><thead><tr><th>Horário-alvo histórico</th><th>Umidade observada (%)</th><th>Umidade prevista (%)</th></tr></thead><tbody>{external.test_examples.map(row=><tr key={row.target_at}><td>{row.target_at.replace('T',' ')}</td><td>{num(row.actual_soil_pct,2)}</td><td>{num(row.predicted_soil_pct,2)}</td></tr>)}</tbody></table></div>}
      </>:<p>{loading?'Consultando experimento…':external?.reason||'Conecte a estação para consultar o experimento externo.'}</p>}
    </section>
    <section className="panel data"><div className="section-title"><h3>Medições no período</h3><button type="button" disabled={!rows.length} onClick={()=>exportCSV(rows)}>Exportar CSV ↓</button></div><div className="table-scroll"><table><caption className="sr-only">Medições do dispositivo selecionado</caption><thead><tr><th>Horário da medição</th><th>Temperatura (°C)</th><th>Umidade do ar (%)</th><th>Solo (bruto)</th></tr></thead><tbody>{rows.length?rows.slice(0,100).map(r=><tr key={r.id}><td>{fmt(r.measured_at)}</td><td>{num(r.temperature_c)}</td><td>{num(r.air_humidity_pct)}</td><td>{num(r.soil_raw,0)}</td></tr>):<tr><td colSpan="4">Nenhuma medição carregada</td></tr>}</tbody></table></div></section><footer>Ambiente · Agentes, IoT e Aprendizado de Máquina<span>React → FastAPI → PostgreSQL</span></footer>
  </main></>;
}
createRoot(document.getElementById('root')).render(<App/>);
