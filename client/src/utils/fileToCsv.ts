import * as XLSX from 'xlsx';

export const SPREADSHEET_ACCEPT = '.csv,.xlsx,.xls';

export function isSpreadsheetFile(name: string): boolean {
  return /\.(csv|xlsx|xls)$/i.test(name);
}

/** Read a contacts file as CSV text, converting Excel workbooks (first sheet) on the fly. */
export async function fileToCsv(file: File): Promise<string> {
  if (/\.(xlsx|xls)$/i.test(file.name)) {
    const workbook = XLSX.read(await file.arrayBuffer(), { cellDates: true });
    const firstSheet = workbook.Sheets[workbook.SheetNames[0]];
    if (!firstSheet) {
      throw new Error('The Excel file has no sheets');
    }
    return XLSX.utils.sheet_to_csv(firstSheet, { blankrows: false });
  }
  return file.text();
}
