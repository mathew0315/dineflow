import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import "./styles.css";
import Home from "./pages/Home";
import OrderPage from "./pages/OrderPage";
import TrackPage from "./pages/TrackPage";
import Login from "./pages/Login";
import AdminLayout from "./admin/AdminLayout";
import Board from "./admin/Board";
import Pos from "./admin/Pos";
import MenuAdmin from "./admin/MenuAdmin";
import Report from "./admin/Report";
import Settings from "./admin/Settings";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/s/:slug" element={<OrderPage />} />
        <Route path="/s/:slug/orders/:id" element={<TrackPage />} />
        <Route path="/login" element={<Login />} />
        <Route path="/admin" element={<AdminLayout />}>
          <Route index element={<Board />} />
          <Route path="pos" element={<Pos />} />
          <Route path="menu" element={<MenuAdmin />} />
          <Route path="report" element={<Report />} />
          <Route path="settings" element={<Settings />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  </StrictMode>,
);
