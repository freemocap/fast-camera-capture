import {darken, Typography} from "@mui/material";
import IconButton from "@mui/material/IconButton";
import CloseIcon from '@mui/icons-material/Close';
import Drawer from "@mui/material/Drawer";
import extendedPaperbaseTheme from "@/layout/base-content/paperbase_theme/paperbase-theme";
export const TerminalDrawer = () => {
    return (
        <Drawer
            variant="permanent"
            sx = {{
            height: '100%',
            width: '100%',
            display: 'flex',
            flexDirection: 'column',
            backgroundColor: extendedPaperbaseTheme.palette.primary.dark,
            borderStyle: 'solid', borderWidth: '5px', borderColor: darken(extendedPaperbaseTheme.palette.primary.dark, 0.9)
        }}>
           <div style={{display: 'flex', justifyContent: "space-between" }}>
               <span style={{color:extendedPaperbaseTheme.palette.primary.contrastText}}>Terminal</span>
               <IconButton size="small">
                   <CloseIcon fontSize="small" color={"primary"}/>
               </IconButton>
           </div>
            <div style={{flex: 1, overflowY: 'auto'}}>
                <Typography sx={{p: 2, color: extendedPaperbaseTheme.palette.primary.contrastText}}>
                    This is a terminal panel. You can add your terminal component here.
                </Typography>
            </div>
        </Drawer>
    );
};
