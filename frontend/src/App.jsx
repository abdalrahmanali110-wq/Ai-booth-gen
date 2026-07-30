import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import Chat from "./pages/Chat/Chat";
import Design from "./pages/Design/Design";
import "./App.css";
import "./pages/Design/Design.css";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/chat" replace />} />
        <Route path="/chat" element={<Chat />} />
        <Route path="/chat/:sessionId" element={<Chat />} />
        <Route path="/design" element={<Design />} />
        <Route path="/design/:sessionId" element={<Design />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
