export const chartOptions = {
  months: [
    'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
  ],

  dateFormats: {
      dateFormatFull: '%b %e, %Y',
      dateFormatMonth: '%b %Y',
      dateFormatyear: '%Y',
  },

  // === Shared style variables ===
  colors: {
    WHITE: '#ffffff',
    TEXT: '#f9fafb',
    GRID: '#303f53',          // dark gray grid lines
    CROSSHAIR: '#5181B8',
    TOOLTIP_BG: 'rgba(15, 23, 42, 0.6)', // dark navy with slight transparency

    // === Primary chart colors ===
//    PRIMARY: '#5181B8',   // blue for income
    PRIMARY: '#2caffe',   // blue for income
    SECONDARY: '#E76F51', // warm orange/red for expenses
    TERT: '#2ECC71', // vibrant green
    QUAT: '#A370F7', // soft violet
  },

  font: {
    FAMILY: 'Arial, sans-serif',
  },

  axis: {
    TICK_WIDTH: 1,
    LINE_WIDTH: 1,
    MINOR_TICK_INTERVAL: 5000,
    TICK_INTERVAL_AMOUNT: 5000,
    TICK_INTERVAL_PERCENT: 50, // 50% step
    LABEL_ROTATION: -45,       // or try -45 or 45 for diagonal
  },

  tooltip: {
    BORDER_WIDTH: 0.1,
  },

  PIE_ALLOC_COLORS: {
  "VUAA.UK": "#1f77b4",
  "CNDX.UK": "#ff7f0e",
  "SPYL.DE": "#2ca02c",
  "IUIT.UK": "#d62728",
  "IGLN.UK": "#9467bd",
  },
};
