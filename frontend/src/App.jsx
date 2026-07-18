import "./App.css";
import { useEffect, useRef, useState } from "react";

const MAX_ROWS = 40;

export default function App() {
  const [ticks, setTicks] = useState([]);
  const [status, setStatus] = useState("connecting");
  const prevPx = useRef({});

  useEffect(() => {
    const ws = new WebSocket("ws://localhost:8000/ws/feed");
    ws.binaryType = "arraybuffer";
    ws.onopen = () => setStatus("live");
    ws.onclose = () => setStatus("disconnected");
    ws.onerror = () => setStatus("error");
    ws.onmessage = (e) => {
      const t = JSON.parse(new TextDecoder().decode(e.data));
      const prev = prevPx.current[t.symbol];
      t.dir = prev == null ? 0 : t.price > prev ? 1 : t.price < prev ? -1 : 0;
      prevPx.current[t.symbol] = t.price;
      setTicks((rows) => [t, ...rows].slice(0, MAX_ROWS));
    };
    return () => ws.close();
  }, []);

  return (
    <div className="app">
      <header>
        <h1>TickDesk</h1>
        <span className={`badge ${status}`}>{status}</span>
      </header>

      <table className="tape">
        <thead>
          <tr>
            <th>time</th>
            <th>symbol</th>
            <th className="num">price</th>
            <th className="num">qty</th>
            <th className="num">bid</th>
            <th className="num">ask</th>
          </tr>
        </thead>
        <tbody>
          {ticks.map((t, i) => (
            <tr key={i} className={t.dir > 0 ? "up" : t.dir < 0 ? "down" : ""}>
              <td className="dim">{new Date(t.ts * 1000).toLocaleTimeString()}</td>
              <td className="sym">{t.symbol}</td>
              <td className="num price">{t.price.toFixed(2)}</td>
              <td className="num dim">{t.qty}</td>
              <td className="num">{t.bid.toFixed(2)}</td>
              <td className="num">{t.ask.toFixed(2)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
