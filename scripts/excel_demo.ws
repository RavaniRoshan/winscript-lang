-- excel_demo.ws
-- Read a value from Excel, compute something, write back

try
    tell Excel
        open "C:/tmp/demo.xlsx"

        tell sheet "Sheet1"
            set sales to value of cell "B2"
            set tax_rate to value of cell "C2"
            declare tax as decimal
            set tax to sales * tax_rate
            set value of cell "D2" to tax
        end tell

        save
        close
    end tell

    return "Tax calculated and written: " & tax

catch err
    return "Excel error: " & err
end try
