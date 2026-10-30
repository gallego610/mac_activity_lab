import java.awt.*;
import java.awt.event.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.time.*;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.List;
import java.util.concurrent.*;
import java.util.concurrent.atomic.*;
import javax.swing.*;
import javax.swing.border.*;
import javax.swing.table.*;

/**
 * Activity Event Generator — versión Java pura (Swing + Robot + AWT).
 * Sin dependencias externas. Compila y ejecuta con cualquier JDK 11+.
 *
 * Compilar:  javac ActivityEventGenerator.java
 * Ejecutar:  java  ActivityEventGenerator
 */
public class ActivityEventGenerator extends JFrame {

    // ── Paleta ────────────────────────────────────────────────────────────────
    static final Color BG      = hex("#0f1117");
    static final Color CARD    = hex("#1a1d27");
    static final Color CARD2   = hex("#22263a");
    static final Color BORDER  = hex("#2e3250");
    static final Color ACCENT  = hex("#6c63ff");
    static final Color ACCENT2 = hex("#00d4aa");
    static final Color ACCENT3 = hex("#ff6b6b");
    static final Color TEXT    = hex("#e8eaf6");
    static final Color DIM     = hex("#7b82b0");
    static final Color GREEN   = hex("#4caf8a");
    static final Color YELLOW  = hex("#f5c842");
    static final Color ORANGE  = hex("#ff9f43");

    static Color hex(String h) {
        return Color.decode(h);
    }

    // ── Estado ────────────────────────────────────────────────────────────────
    private final Robot robot;
    private ScheduledExecutorService scheduler;
    private ScheduledFuture<?> genTask;
    private ScheduledFuture<?> timerTask;
    private ScheduledFuture<?> idleTask;

    private final AtomicBoolean genRunning  = new AtomicBoolean(false);
    private final AtomicBoolean autoRunning = new AtomicBoolean(false);
    private final AtomicLong    startedAt   = new AtomicLong(0);
    private final AtomicLong    lastTickAt  = new AtomicLong(0);
    private final AtomicLong    lastActivity= new AtomicLong(System.currentTimeMillis());
    private final AtomicInteger eventCount  = new AtomicInteger(0);
    private int currentInterval = 120;

    // Datos del log para exportar
    private final List<String[]> logData = Collections.synchronizedList(new ArrayList<>());

    // ── UI ────────────────────────────────────────────────────────────────────
    private JLabel        catLabel;
    private JLabel        statusBadge;
    private JLabel        bCount, bElapsed, bNext, bIdle;
    private JButton       btnStart, btnAuto, btnStop;
    private JSpinner      spInterval, spQuantity, spIdleSecs;
    private JComboBox<String> cbAction, cbEventType;
    private DefaultTableModel logModel;
    private JTable        logTable;
    private JScrollPane   logScroll;
    private JLabel        warnLabel;

    // Animación gatito
    private final String[] CAT_FRAMES = {"😺 ～","😸 ♪","🐱 ！","😻 ★","😺 ～","🐱 ♫"};
    private int catFrame = 0;
    private javax.swing.Timer catTimer;

    // ── Constructor ───────────────────────────────────────────────────────────
    public ActivityEventGenerator() {
        super("Activity Event Generator");

        // Robot para generar eventos
        Robot r = null;
        try { r = new Robot(); r.setAutoDelay(10); } catch (AWTException e) {
            showError("No se pudo inicializar Robot:\n" + e.getMessage());
        }
        robot = r;

        scheduler = Executors.newScheduledThreadPool(3);
        buildUI();
        registerGlobalActivityListener();
        setDefaultCloseOperation(DO_NOTHING_ON_CLOSE);
        addWindowListener(new WindowAdapter() {
            public void windowClosing(WindowEvent e) { shutdown(); }
        });
        setMinimumSize(new Dimension(860, 620));
        setSize(920, 680);
        setLocationRelativeTo(null);
        setVisible(true);
    }

    // ─────────────────────────────────────────────────────────────────────────
    // UI
    // ─────────────────────────────────────────────────────────────────────────
    private void buildUI() {
        JPanel outer = new JPanel();
        outer.setLayout(new BoxLayout(outer, BoxLayout.Y_AXIS));
        outer.setBackground(BG);
        outer.setBorder(new EmptyBorder(18, 22, 12, 22));

        outer.add(buildHeader());
        outer.add(vgap(10));
        outer.add(buildEventCard());
        outer.add(vgap(10));
        outer.add(buildAutoCard());
        outer.add(vgap(10));
        outer.add(buildButtons());
        outer.add(vgap(10));
        outer.add(buildBadges());
        outer.add(vgap(10));
        outer.add(buildLog());
        outer.add(vgap(8));
        outer.add(buildFooter());

        JScrollPane scroll = new JScrollPane(outer);
        scroll.setBorder(null);
        scroll.getViewport().setBackground(BG);
        scroll.setVerticalScrollBarPolicy(JScrollPane.VERTICAL_SCROLLBAR_AS_NEEDED);
        scroll.setHorizontalScrollBarPolicy(JScrollPane.HORIZONTAL_SCROLLBAR_NEVER);
        add(scroll);
    }

    // ── Encabezado ────────────────────────────────────────────────────────────
    private JPanel buildHeader() {
        JPanel p = row(BG);

        JLabel dot = new JLabel("●");
        dot.setForeground(ACCENT);
        dot.setFont(new Font("SansSerif", Font.BOLD, 12));
        p.add(dot);
        p.add(hgap(8));

        JLabel title = new JLabel("Activity Event Generator");
        title.setForeground(TEXT);
        title.setFont(new Font("SansSerif", Font.BOLD, 20));
        p.add(title);
        p.add(hgap(14));

        catLabel = new JLabel("😴 zzz");
        catLabel.setForeground(ACCENT2);
        catLabel.setFont(new Font("Segoe UI Emoji", Font.PLAIN, 16));
        p.add(catLabel);

        return p;
    }

    // ── Tarjeta configuración del evento ──────────────────────────────────────
    private JPanel buildEventCard() {
        JPanel card = card();

        JLabel title = label("CONFIGURACIÓN DEL EVENTO", ACCENT, 9, Font.BOLD);
        title.setAlignmentX(LEFT_ALIGNMENT);
        card.add(title);
        card.add(vgap(10));

        JPanel fields = new JPanel(new GridLayout(1, 4, 12, 0));
        fields.setBackground(CARD);
        fields.setAlignmentX(LEFT_ALIGNMENT);
        fields.setMaximumSize(new Dimension(Integer.MAX_VALUE, 60));

        spInterval = spinner(120, 1, 86400);
        spQuantity = spinner(1, 1, 10);
        cbAction   = combo(new String[]{"Generar evento", "Solo registrar (sin acción)"});
        cbEventType= combo(new String[]{"izquierdo", "derecho", "central"});

        fields.add(field("Intervalo (segundos)", spInterval));
        fields.add(field("Acción al disparar",   cbAction));
        fields.add(field("Tipo de evento",        cbEventType));
        fields.add(field("Cantidad",              spQuantity));
        card.add(fields);

        if (robot == null) {
            card.add(vgap(8));
            warnLabel = label("⚠  Robot no disponible — verifica permisos de accesibilidad", YELLOW, 9, Font.PLAIN);
            warnLabel.setAlignmentX(LEFT_ALIGNMENT);
            card.add(warnLabel);
        }
        return card;
    }

    // ── Tarjeta temporizador inteligente ──────────────────────────────────────
    private JPanel buildAutoCard() {
        JPanel card = card();

        JLabel title = label("TEMPORIZADOR INTELIGENTE", ORANGE, 9, Font.BOLD);
        title.setAlignmentX(LEFT_ALIGNMENT);
        card.add(title);
        card.add(vgap(10));

        JPanel row = new JPanel(new FlowLayout(FlowLayout.LEFT, 0, 0));
        row.setBackground(CARD);
        row.setAlignmentX(LEFT_ALIGNMENT);

        spIdleSecs = spinner(180, 5, 86400);
        row.add(field("Espera previa (segundos)", spIdleSecs));
        row.add(hgap(20));

        JLabel hint = label(
            "<html>El generador aguarda este tiempo antes de iniciar.<br>" +
            "Si se detecta actividad, reinicia la espera.</html>",
            DIM, 10, Font.PLAIN);
        row.add(hint);
        card.add(row);
        return card;
    }

    // ── Botones ───────────────────────────────────────────────────────────────
    private JPanel buildButtons() {
        JPanel p = row(BG);
        p.setAlignmentX(LEFT_ALIGNMENT);

        btnStart = flatBtn("▶  Iniciar generador", ACCENT);
        btnAuto  = flatBtn("⏱  Inicio automático", ORANGE);
        btnStop  = flatBtn("⏹  Detener",           ACCENT3);
        JButton btnExport = flatBtn("Exportar…",   BORDER);
        JButton btnClear  = flatBtn("Limpiar",      BORDER);

        btnStop.setEnabled(false);

        btnStart.addActionListener(e -> startGenerator());
        btnAuto .addActionListener(e -> toggleAuto());
        btnStop .addActionListener(e -> stopGenerator("Detenido por el usuario"));
        btnExport.addActionListener(e -> exportLog());
        btnClear .addActionListener(e -> clearLog());

        p.add(btnStart); p.add(hgap(10));
        p.add(btnAuto);  p.add(hgap(10));
        p.add(btnStop);  p.add(hgap(10));
        p.add(btnExport);p.add(hgap(10));
        p.add(btnClear);
        return p;
    }

    // ── Badges de estado ──────────────────────────────────────────────────────
    private JPanel buildBadges() {
        JPanel p = new JPanel(new GridLayout(1, 5, 8, 0));
        p.setBackground(BG);
        p.setAlignmentX(LEFT_ALIGNMENT);
        p.setMaximumSize(new Dimension(Integer.MAX_VALUE, 60));

        statusBadge = new JLabel("Inactivo", SwingConstants.CENTER);
        statusBadge.setForeground(DIM);
        statusBadge.setBackground(BORDER);
        statusBadge.setFont(new Font("SansSerif", Font.BOLD, 12));
        statusBadge.setOpaque(true);
        statusBadge.setBorder(new RoundedBorder(8, BORDER));

        bCount   = badgeValue("0",        ACCENT);
        bElapsed = badgeValue("00:00:00", TEXT);
        bNext    = badgeValue("--:--",    ACCENT2);
        bIdle    = badgeValue("--:--",    ORANGE);

        p.add(statusBadge);
        p.add(badge("Eventos generados",     bCount));
        p.add(badge("Tiempo activo",         bElapsed));
        p.add(badge("Próximo evento en",     bNext));
        p.add(badge("Inicio automático en",  bIdle));
        return p;
    }

    // ── Log ───────────────────────────────────────────────────────────────────
    private JPanel buildLog() {
        JPanel card = new JPanel(new BorderLayout());
        card.setBackground(CARD);
        card.setBorder(new RoundedBorder(10, CARD));
        card.setAlignmentX(LEFT_ALIGNMENT);

        JLabel hdr = label("REGISTRO DE EVENTOS GENERADOS", ACCENT, 9, Font.BOLD);
        hdr.setBorder(new EmptyBorder(10, 14, 8, 14));
        card.add(hdr, BorderLayout.NORTH);

        logModel = new DefaultTableModel(new String[]{"Hora", "Evento generado", "Detalle"}, 0) {
            public boolean isCellEditable(int r, int c) { return false; }
        };
        logTable = new JTable(logModel);
        styleTable();

        logScroll = new JScrollPane(logTable);
        logScroll.setBorder(null);
        logScroll.getViewport().setBackground(CARD);
        logScroll.setPreferredSize(new Dimension(0, 180));
        card.add(logScroll, BorderLayout.CENTER);
        return card;
    }

    private void styleTable() {
        logTable.setBackground(CARD);
        logTable.setForeground(TEXT);
        logTable.setFont(new Font("SansSerif", Font.PLAIN, 11));
        logTable.setRowHeight(24);
        logTable.setShowGrid(false);
        logTable.setIntercellSpacing(new Dimension(0, 0));
        logTable.setSelectionBackground(ACCENT);
        logTable.setSelectionForeground(TEXT);
        logTable.getTableHeader().setBackground(BORDER);
        logTable.getTableHeader().setForeground(DIM);
        logTable.getTableHeader().setFont(new Font("SansSerif", Font.BOLD, 9));
        logTable.getTableHeader().setBorder(BorderFactory.createEmptyBorder());
        logTable.getColumnModel().getColumn(0).setPreferredWidth(165);
        logTable.getColumnModel().getColumn(1).setPreferredWidth(185);
        logTable.getColumnModel().getColumn(2).setPreferredWidth(400);
        logTable.setDefaultRenderer(Object.class, new DefaultTableCellRenderer() {
            public Component getTableCellRendererComponent(
                    JTable t, Object v, boolean sel, boolean foc, int r, int c) {
                super.getTableCellRendererComponent(t, v, sel, foc, r, c);
                setOpaque(true);
                setBorder(new EmptyBorder(0, 10, 0, 10));
                if (sel) {
                    setBackground(ACCENT); setForeground(TEXT);
                } else {
                    setBackground(r % 2 == 0 ? CARD : CARD2);
                    setForeground(c == 1 ? ACCENT2 : c == 0 ? DIM : TEXT);
                }
                return this;
            }
        });
    }

    private JLabel buildFooter() {
        JLabel f = label(
            "⚡ Failsafe: lleva el cursor a la esquina superior-izquierda para abortar.",
            DIM, 8, Font.PLAIN);
        f.setAlignmentX(LEFT_ALIGNMENT);
        return f;
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Lógica del generador
    // ─────────────────────────────────────────────────────────────────────────
    private void startGenerator() {
        if (genRunning.get()) return;
        currentInterval = (int) spInterval.getValue();
        genRunning.set(true);
        startedAt.set(System.currentTimeMillis());
        lastTickAt.set(System.currentTimeMillis());

        SwingUtilities.invokeLater(() -> {
            setStatus("Generando eventos", GREEN, BG);
            btnStart.setEnabled(false);
            btnStop.setEnabled(true);
            startCat();
        });

        record("Generador iniciado",
               "Intervalo: " + currentInterval + " s · acción: " + cbAction.getSelectedItem());

        genTask = scheduler.scheduleAtFixedRate(() -> {
            lastTickAt.set(System.currentTimeMillis());
            String[] result = fireEvent();
            SwingUtilities.invokeLater(() -> addRow(result[0], result[1]));
        }, currentInterval, currentInterval, TimeUnit.SECONDS);

        timerTask = scheduler.scheduleAtFixedRate(this::updateTimers, 1, 1, TimeUnit.SECONDS);
    }

    private void stopGenerator(String reason) {
        if (!genRunning.get()) return;
        genRunning.set(false);
        if (genTask   != null) { genTask.cancel(false);   genTask   = null; }
        if (timerTask != null) { timerTask.cancel(false); timerTask = null; }

        SwingUtilities.invokeLater(() -> {
            btnStart.setEnabled(true);
            btnStop.setEnabled(false);
            bNext.setText("--:--");
            stopCat();
            if (autoRunning.get()) setStatus("En espera", ORANGE, BG);
            else                   setStatus("Inactivo",  BORDER, DIM);
            addRow("Generador detenido", reason);
        });
    }

    private String[] fireEvent() {
        String action = (String) cbAction.getSelectedItem();
        if (!"Generar evento".equals(action)) {
            return new String[]{"Evento registrado", "Sin acción en el sistema"};
        }
        if (robot == null) {
            return new String[]{"Evento (sin efecto)", "Robot no disponible"};
        }
        try {
            PointerInfo pi  = MouseInfo.getPointerInfo();
            Point pos       = pi.getLocation();
            String typeStr  = (String) cbEventType.getSelectedItem();
            int    qty      = (int) spQuantity.getValue();
            int    btn      = buttonCode(typeStr);

            // Failsafe: esquina superior-izquierda
            Dimension screen = Toolkit.getDefaultToolkit().getScreenSize();
            if (pos.x <= 5 && pos.y <= 5) {
                SwingUtilities.invokeLater(() -> stopGenerator("⚡ Failsafe activado"));
                return new String[]{"⚡ Failsafe", "Cursor en esquina — generador detenido"};
            }

            for (int i = 0; i < qty; i++) {
                robot.mousePress(btn);
                robot.mouseRelease(btn);
                if (i < qty - 1) robot.delay(80);
            }
            return new String[]{
                "Evento generado",
                "Tipo: " + typeStr + " · cantidad: " + qty +
                " · posición: (" + pos.x + ", " + pos.y + ")"
            };
        } catch (Exception e) {
            return new String[]{"Error", e.getMessage()};
        }
    }

    private int buttonCode(String type) {
        return switch (type) {
            case "derecho"  -> InputEvent.BUTTON3_DOWN_MASK;
            case "central"  -> InputEvent.BUTTON2_DOWN_MASK;
            default         -> InputEvent.BUTTON1_DOWN_MASK;
        };
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Temporizador inteligente (inactividad)
    // ─────────────────────────────────────────────────────────────────────────
    private void registerGlobalActivityListener() {
        // AWTEventListener captura eventos globales dentro de la JVM;
        // para eventos fuera de la ventana usamos un poller de posición del cursor.
        long mask = AWTEvent.MOUSE_EVENT_MASK
                  | AWTEvent.MOUSE_MOTION_EVENT_MASK
                  | AWTEvent.KEY_EVENT_MASK
                  | AWTEvent.MOUSE_WHEEL_EVENT_MASK;
        Toolkit.getDefaultToolkit().addAWTEventListener(
            e -> lastActivity.set(System.currentTimeMillis()), mask);

        // Poller de posición del cursor (detecta movimiento fuera de la ventana)
        final Point[] lastPos = { MouseInfo.getPointerInfo().getLocation() };
        scheduler.scheduleAtFixedRate(() -> {
            Point cur = MouseInfo.getPointerInfo().getLocation();
            if (!cur.equals(lastPos[0])) {
                lastActivity.set(System.currentTimeMillis());
                lastPos[0] = cur;
            }
        }, 0, 500, TimeUnit.MILLISECONDS);
    }

    private void toggleAuto() {
        if (!autoRunning.get()) {
            int idleSecs = (int) spIdleSecs.getValue();
            autoRunning.set(true);
            lastActivity.set(System.currentTimeMillis());

            btnAuto.setText("⏱  Cancelar automático");
            btnAuto.setBackground(BORDER);
            setStatus("En espera", ORANGE, BG);
            record("Inicio automático activado", "Espera previa: " + idleSecs + " s");

            idleTask = scheduler.scheduleAtFixedRate(() -> {
                if (!autoRunning.get()) return;
                long idle      = (System.currentTimeMillis() - lastActivity.get()) / 1000;
                int  threshold = (int) spIdleSecs.getValue();

                if (idle >= threshold && !genRunning.get()) {
                    SwingUtilities.invokeLater(() -> {
                        record("▶ Generador iniciado", "Inicio automático por temporizador");
                        startGenerator();
                    });
                }
                if (idle < 2 && genRunning.get()) {
                    SwingUtilities.invokeLater(() -> {
                        record("⏹ Generador pausado", "En espera — temporizador reiniciado");
                        stopGenerator("En espera — temporizador reiniciado");
                    });
                }
                // Actualizar badge de cuenta regresiva
                long remaining = Math.max(0, threshold - idle);
                SwingUtilities.invokeLater(() -> bIdle.setText(fmtMS(remaining)));
            }, 1, 1, TimeUnit.SECONDS);

        } else {
            autoRunning.set(false);
            if (idleTask != null) { idleTask.cancel(false); idleTask = null; }
            btnAuto.setText("⏱  Inicio automático");
            btnAuto.setBackground(ORANGE);
            bIdle.setText("--:--");
            if (!genRunning.get()) setStatus("Inactivo", BORDER, DIM);
            record("Inicio automático desactivado", "");
        }
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Timers y log
    // ─────────────────────────────────────────────────────────────────────────
    private void updateTimers() {
        if (!genRunning.get()) return;
        long elapsed   = (System.currentTimeMillis() - startedAt.get())  / 1000;
        long remaining = Math.max(0,
            currentInterval - (System.currentTimeMillis() - lastTickAt.get()) / 1000);
        SwingUtilities.invokeLater(() -> {
            bElapsed.setText(fmtHMS(elapsed));
            bNext.setText(fmtMS(remaining));
        });
    }

    private void record(String event, String detail) {
        String stamp = DateTimeFormatter.ISO_OFFSET_DATE_TIME
            .format(ZonedDateTime.now().withNano(0));
        logData.add(new String[]{stamp, event, detail});
        SwingUtilities.invokeLater(() -> addRow(event, detail));
    }

    private void addRow(String event, String detail) {
        String stamp = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss")
            .format(LocalDateTime.now());
        logModel.addRow(new Object[]{stamp, event, detail});
        eventCount.incrementAndGet();
        bCount.setText(String.valueOf(eventCount.get()));
        int last = logModel.getRowCount() - 1;
        logTable.scrollRectToVisible(logTable.getCellRect(last, 0, true));
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Exportar / Limpiar
    // ─────────────────────────────────────────────────────────────────────────
    private void exportLog() {
        if (logData.isEmpty()) {
            JOptionPane.showMessageDialog(this, "No hay eventos para exportar.", "Sin eventos",
                JOptionPane.INFORMATION_MESSAGE);
            return;
        }
        JFileChooser fc = new JFileChooser();
        fc.setSelectedFile(new File("activity_event_generator_log.json"));
        if (fc.showSaveDialog(this) != JFileChooser.APPROVE_OPTION) return;
        try {
            StringBuilder sb = new StringBuilder("[\n");
            synchronized (logData) {
                for (int i = 0; i < logData.size(); i++) {
                    String[] row = logData.get(i);
                    sb.append("  {")
                      .append("\"timestamp\":\"").append(row[0]).append("\",")
                      .append("\"event\":\"").append(escape(row[1])).append("\",")
                      .append("\"detail\":\"").append(escape(row[2])).append("\"}")
                      .append(i < logData.size() - 1 ? "," : "").append("\n");
                }
            }
            sb.append("]");
            Files.writeString(fc.getSelectedFile().toPath(), sb.toString(),
                StandardCharsets.UTF_8);
            JOptionPane.showMessageDialog(this,
                "Registro guardado en:\n" + fc.getSelectedFile().getAbsolutePath(),
                "Exportación completada", JOptionPane.INFORMATION_MESSAGE);
        } catch (IOException ex) {
            showError("Error al exportar: " + ex.getMessage());
        }
    }

    private void clearLog() {
        if (genRunning.get()) {
            JOptionPane.showMessageDialog(this,
                "Detén el generador antes de limpiar el registro.",
                "Generador activo", JOptionPane.WARNING_MESSAGE);
            return;
        }
        logData.clear();
        logModel.setRowCount(0);
        eventCount.set(0);
        bCount.setText("0");
        bElapsed.setText("00:00:00");
        bNext.setText("--:--");
        startedAt.set(0);
        lastTickAt.set(0);
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Animación gatito
    // ─────────────────────────────────────────────────────────────────────────
    private void startCat() {
        if (catTimer != null && catTimer.isRunning()) return;
        catTimer = new javax.swing.Timer(400, e -> {
            catLabel.setText(CAT_FRAMES[catFrame % CAT_FRAMES.length]);
            catFrame++;
        });
        catTimer.start();
    }

    private void stopCat() {
        if (catTimer != null) catTimer.stop();
        catFrame = 0;
        catLabel.setText("😴 zzz");
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Helpers UI
    // ─────────────────────────────────────────────────────────────────────────
    private JPanel card() {
        JPanel p = new JPanel();
        p.setLayout(new BoxLayout(p, BoxLayout.Y_AXIS));
        p.setBackground(CARD);
        p.setBorder(new CompoundBorder(
            new RoundedBorder(10, CARD),
            new EmptyBorder(14, 18, 14, 18)));
        p.setAlignmentX(LEFT_ALIGNMENT);
        p.setMaximumSize(new Dimension(Integer.MAX_VALUE, Integer.MAX_VALUE));
        return p;
    }

    private JPanel row(Color bg) {
        JPanel p = new JPanel(new FlowLayout(FlowLayout.LEFT, 0, 0));
        p.setBackground(bg);
        p.setAlignmentX(LEFT_ALIGNMENT);
        return p;
    }

    private JPanel field(String labelText, JComponent control) {
        JPanel p = new JPanel();
        p.setLayout(new BoxLayout(p, BoxLayout.Y_AXIS));
        p.setBackground(control.getBackground().equals(CARD2) ? CARD : control.getParent() != null ? CARD : CARD);
        p.setBackground(CARD);
        JLabel lbl = label(labelText.toUpperCase(), DIM, 9, Font.PLAIN);
        lbl.setBorder(new EmptyBorder(0, 0, 4, 0));
        lbl.setAlignmentX(LEFT_ALIGNMENT);
        control.setAlignmentX(LEFT_ALIGNMENT);
        p.add(lbl);
        p.add(control);
        return p;
    }

    private JPanel badge(String titleText, JLabel valueLabel) {
        JPanel p = new JPanel();
        p.setLayout(new BoxLayout(p, BoxLayout.Y_AXIS));
        p.setBackground(CARD2);
        p.setBorder(new CompoundBorder(
            new RoundedBorder(8, CARD2),
            new EmptyBorder(8, 14, 8, 14)));
        JLabel t = label(titleText, DIM, 8, Font.PLAIN);
        t.setAlignmentX(LEFT_ALIGNMENT);
        valueLabel.setAlignmentX(LEFT_ALIGNMENT);
        p.add(t);
        p.add(valueLabel);
        return p;
    }

    private JLabel badgeValue(String text, Color color) {
        JLabel l = new JLabel(text);
        l.setForeground(color);
        l.setFont(new Font("SansSerif", Font.BOLD, 15));
        return l;
    }

    private JButton flatBtn(String text, Color bg) {
        JButton b = new JButton(text) {
            protected void paintComponent(Graphics g) {
                Graphics2D g2 = (Graphics2D) g.create();
                g2.setRenderingHint(RenderingHints.KEY_ANTIALIASING,
                                    RenderingHints.VALUE_ANTIALIAS_ON);
                g2.setColor(isEnabled() ? bg : BORDER);
                g2.fillRoundRect(0, 0, getWidth(), getHeight(), 10, 10);
                g2.setColor(isEnabled() ? TEXT : DIM);
                g2.setFont(getFont());
                FontMetrics fm = g2.getFontMetrics();
                int x = (getWidth()  - fm.stringWidth(getText())) / 2;
                int y = (getHeight() + fm.getAscent() - fm.getDescent()) / 2;
                g2.drawString(getText(), x, y);
                g2.dispose();
            }
        };
        b.setFont(new Font("Segoe UI Emoji", Font.BOLD, 12));
        b.setPreferredSize(new Dimension(textWidth(text) + 36, 38));
        b.setBackground(bg);
        b.setForeground(TEXT);
        b.setBorderPainted(false);
        b.setFocusPainted(false);
        b.setContentAreaFilled(false);
        b.setCursor(Cursor.getPredefinedCursor(Cursor.HAND_CURSOR));
        return b;
    }

    private int textWidth(String text) {
        return new JLabel(text).getFontMetrics(
            new Font("Segoe UI Emoji", Font.BOLD, 12)).stringWidth(text);
    }

    private JSpinner spinner(int val, int min, int max) {
        JSpinner s = new JSpinner(new SpinnerNumberModel(val, min, max, 1));
        s.setBackground(CARD2);
        s.setForeground(TEXT);
        s.setFont(new Font("SansSerif", Font.PLAIN, 12));
        s.setMaximumSize(new Dimension(Integer.MAX_VALUE, 30));
        JComponent editor = s.getEditor();
        if (editor instanceof JSpinner.DefaultEditor de) {
            de.getTextField().setBackground(CARD2);
            de.getTextField().setForeground(TEXT);
            de.getTextField().setCaretColor(TEXT);
            de.getTextField().setBorder(BorderFactory.createEmptyBorder(4, 6, 4, 6));
        }
        return s;
    }

    private JComboBox<String> combo(String[] items) {
        JComboBox<String> cb = new JComboBox<>(items);
        cb.setBackground(CARD2);
        cb.setForeground(TEXT);
        cb.setFont(new Font("SansSerif", Font.PLAIN, 12));
        cb.setMaximumSize(new Dimension(Integer.MAX_VALUE, 30));
        cb.setBorder(BorderFactory.createEmptyBorder(2, 4, 2, 4));
        cb.setRenderer((list, value, index, isSelected, cellHasFocus) -> {
            JLabel l = new JLabel(value);
            l.setBackground(isSelected ? ACCENT : CARD2);
            l.setForeground(TEXT);
            l.setFont(new Font("SansSerif", Font.PLAIN, 12));
            l.setBorder(new EmptyBorder(4, 8, 4, 8));
            l.setOpaque(true);
            return l;
        });
        return cb;
    }

    private JLabel label(String text, Color fg, int size, int style) {
        JLabel l = new JLabel(text);
        l.setForeground(fg);
        l.setFont(new Font("SansSerif", style, size));
        return l;
    }

    private Component hgap(int w) { return Box.createHorizontalStrut(w); }
    private Component vgap(int h) { return Box.createVerticalStrut(h);   }

    private void setStatus(String text, Color bg, Color fg) {
        statusBadge.setText(text);
        statusBadge.setBackground(bg);
        statusBadge.setForeground(fg);
    }

    private void showError(String msg) {
        JOptionPane.showMessageDialog(this, msg, "Error", JOptionPane.ERROR_MESSAGE);
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Helpers formato
    // ─────────────────────────────────────────────────────────────────────────
    private String fmtHMS(long secs) {
        return String.format("%02d:%02d:%02d",
            secs / 3600, (secs % 3600) / 60, secs % 60);
    }
    private String fmtMS(long secs) {
        return String.format("%02d:%02d", secs / 60, secs % 60);
    }
    private String escape(String s) {
        return s.replace("\\", "\\\\").replace("\"", "\\\"");
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Cierre
    // ─────────────────────────────────────────────────────────────────────────
    private void shutdown() {
        if (genTask   != null) genTask.cancel(false);
        if (timerTask != null) timerTask.cancel(false);
        if (idleTask  != null) idleTask.cancel(false);
        if (catTimer  != null) catTimer.stop();
        scheduler.shutdownNow();
        dispose();
        System.exit(0);
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Borde redondeado (no existe en Swing estándar)
    // ─────────────────────────────────────────────────────────────────────────
    static class RoundedBorder extends AbstractBorder {
        private final int radius;
        private final Color color;
        RoundedBorder(int radius, Color color) {
            this.radius = radius; this.color = color;
        }
        public void paintBorder(Component c, Graphics g, int x, int y, int w, int h) {
            Graphics2D g2 = (Graphics2D) g.create();
            g2.setRenderingHint(RenderingHints.KEY_ANTIALIASING,
                                RenderingHints.VALUE_ANTIALIAS_ON);
            g2.setColor(color);
            g2.drawRoundRect(x, y, w - 1, h - 1, radius, radius);
            g2.dispose();
        }
        public Insets getBorderInsets(Component c) { return new Insets(radius/2,radius/2,radius/2,radius/2); }
        public Insets getBorderInsets(Component c, Insets i) {
            i.set(radius/2, radius/2, radius/2, radius/2); return i;
        }
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Main
    // ─────────────────────────────────────────────────────────────────────────
    public static void main(String[] args) {
        // Look & feel del sistema para mejor integración
        try { UIManager.setLookAndFeel(UIManager.getCrossPlatformLookAndFeelClassName()); }
        catch (Exception ignored) {}

        // Habilitar emojis en macOS
        System.setProperty("apple.awt.application.name", "Activity Event Generator");

        SwingUtilities.invokeLater(ActivityEventGenerator::new);
    }
}
